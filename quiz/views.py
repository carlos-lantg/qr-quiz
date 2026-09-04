import json
import os

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.core import signing
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from .models import Participant, Question, Response, State, ensure_seed, get_state

LETTERS = ["A", "B", "C", "D"]
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "123456")
ADMIN_COOKIE = "quiz_admin"


def _pct(correct, total):
    return round(correct * 100 / total) if total else 0


def _stats():
    """Totales globales + una fila por pregunta, en una sola consulta."""
    questions = []
    grand_total = grand_correct = 0

    rows = Question.objects.annotate(
        n_total=Count("responses"),
        n_correct=Count("responses", filter=Q(responses__is_correct=True)),
    )
    for question in rows:
        grand_total += question.n_total
        grand_correct += question.n_correct
        questions.append(
            {
                "id": question.id,
                "text": question.text,
                "total": question.n_total,
                "correct": question.n_correct,
                "incorrect": question.n_total - question.n_correct,
                "percentage": _pct(question.n_correct, question.n_total),
            }
        )

    state = get_state()
    n_questions = len(questions)
    n_participants = Participant.objects.count()

    # Un participante "completo" respondio todas las preguntas.
    completed = 0
    if n_questions:
        completed = (
            Response.objects.values("participant_uuid")
            .annotate(n=Count("id"))
            .filter(n__gte=n_questions)
            .count()
        )

    done = state.finished or (
        state.started and n_participants > 0 and completed >= n_participants
    )

    return {
        "total": grand_total,
        "correct": grand_correct,
        "incorrect": grand_total - grand_correct,
        "percentage": _pct(grand_correct, grand_total),
        "questions": questions,
        "started": state.started,
        "done": done,
        "participants": n_participants,
        "completed": completed,
    }


@never_cache
def dashboard(request):
    ensure_seed()
    answer_url = (settings.BASE_URL or f"{request.scheme}://{request.get_host()}") + "/answer/"
    qr = qrcode.make(answer_url, image_factory=qrcode.image.svg.SvgPathImage, border=1)
    return render(
        request,
        "dashboard.html",
        {
            "answer_url": answer_url,
            "qr_svg": qr.to_string().decode(),
            "stats": _stats(),
        },
    )


def logo(request):
    response = FileResponse(
        open(settings.BASE_DIR / "logo.jpg", "rb"), content_type="image/jpeg"
    )
    response["Cache-Control"] = "public, max-age=86400"
    return response


@never_cache
def answer(request):
    ensure_seed()
    questions = [
        {
            "id": question.id,
            "text": question.text,
            "options": list(zip(range(4), LETTERS, question.options)),
        }
        for question in Question.objects.all()
    ]
    return render(request, "answer.html", {"questions": questions})


@csrf_exempt
def api_answer(request):
    if request.method != "POST":
        return JsonResponse({"error": "method"}, status=405)

    try:
        data = json.loads(request.body or "{}")
        uuid = str(data["uuid"])[:64]
        option = int(data["option"])
        question = Question.objects.get(pk=data["question"])
    except (ValueError, KeyError, TypeError, Question.DoesNotExist):
        return JsonResponse({"error": "datos invalidos"}, status=400)

    if not uuid or option not in (0, 1, 2, 3):
        return JsonResponse({"error": "datos invalidos"}, status=400)

    if not get_state().started:
        return JsonResponse({"error": "aun no comienza"}, status=409)
    if not Participant.objects.filter(uuid=uuid).exists():
        return JsonResponse({"error": "no estas inscrito"}, status=403)

    try:
        Response.objects.create(
            question=question,
            participant_uuid=uuid,
            selected_option=option,
            is_correct=option == question.correct_option,
        )
    except IntegrityError:
        return JsonResponse({"error": "ya respondiste"}, status=409)

    # No se devuelve is_correct: el participante no debe saber si acerto.
    return JsonResponse({"ok": True})


@never_cache
def api_stats(request):
    return JsonResponse(_stats())


@never_cache
@csrf_exempt
def api_join(request):
    """El movil se registra al abrir /answer/. Cierra al dar Comenzar."""
    try:
        uuid = str(json.loads(request.body or "{}")["uuid"])[:64]
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"error": "datos invalidos"}, status=400)

    if not uuid:
        return JsonResponse({"error": "datos invalidos"}, status=400)

    if not Participant.objects.filter(uuid=uuid).exists():
        if get_state().started:
            return JsonResponse({"error": "cerrado"}, status=403)
        Participant.objects.get_or_create(uuid=uuid)

    # La verdad de "ya respondi" vive en el servidor, no en el telefono: asi un
    # "Reiniciar evento" desbloquea todos los moviles sin borrarles el cache.
    return JsonResponse(
        {
            "ok": True,
            "answered": list(
                Response.objects.filter(participant_uuid=uuid).values_list(
                    "question_id", flat=True
                )
            ),
        }
    )


@csrf_exempt
def api_start(request):
    State.objects.filter(pk=get_state().pk).update(started=True)
    return JsonResponse(_stats())


@csrf_exempt
def api_finish(request):
    State.objects.filter(pk=get_state().pk).update(finished=True)
    return JsonResponse(_stats())


# ---------------------------------------------------------------------------
# Admin: clave unica hardcodeada, cookie firmada, sin usuarios ni sesiones.
# ---------------------------------------------------------------------------


def _is_admin(request):
    try:
        return signing.loads(request.COOKIES.get(ADMIN_COOKIE, ""), max_age=86400) == "ok"
    except signing.BadSignature:
        return False


@never_cache
@csrf_exempt
def admin(request):
    if not _is_admin(request):
        if request.method == "POST" and request.POST.get("password") == ADMIN_PASSWORD:
            response = HttpResponseRedirect("/admin/")
            response.set_cookie(ADMIN_COOKIE, signing.dumps("ok"), max_age=86400)
            return response
        return render(
            request, "admin.html", {"login": True, "error": request.method == "POST"}
        )

    ensure_seed()
    action = request.POST.get("action")

    if action == "reset":
        Response.objects.all().delete()
        Participant.objects.all().delete()
        State.objects.filter(pk=get_state().pk).update(started=False, finished=False)

    elif action == "save_all":
        # Un solo submit trae TODAS las preguntas: las existentes se
        # actualizan, las nuevas (key "newN") se crean y las que no vinieron
        # en el formulario se borran.
        keep = []
        for key in request.POST.getlist("qid"):
            text = request.POST.get(f"text_{key}", "").strip()
            options = [request.POST.get(f"option_{key}_{i}", "").strip() for i in range(4)]
            try:
                correct = int(request.POST.get(f"correct_{key}", 0))
            except (TypeError, ValueError):
                correct = 0
            if correct not in (0, 1, 2, 3):
                correct = 0
            if not text:
                continue  # bloque vacio: se descarta

            if key.startswith("new"):
                keep.append(
                    Question.objects.create(
                        text=text, options=options, correct_option=correct
                    ).id
                )
            elif key.isdigit():
                Question.objects.filter(pk=key).update(
                    text=text, options=options, correct_option=correct
                )
                keep.append(int(key))

        Question.objects.exclude(id__in=keep).delete()

    if action:
        return HttpResponseRedirect("/admin/?ok=1")

    stats = _stats()
    counts = {q["id"]: q["total"] for q in stats["questions"]}
    return render(
        request,
        "admin.html",
        {
            "questions": [
                {
                    "id": question.id,
                    "text": question.text,
                    "correct_option": question.correct_option,
                    "options": list(zip(range(4), LETTERS, question.options)),
                    "n_responses": counts.get(question.id, 0),
                }
                for question in Question.objects.all()
            ],
            "stats": stats,
            "saved": request.GET.get("ok") == "1",
        },
    )


def admin_logout(request):
    response = HttpResponseRedirect("/admin/")
    response.delete_cookie(ADMIN_COOKIE)
    return response
