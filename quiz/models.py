from django.conf import settings
from django.db import models


class Question(models.Model):
    text = models.CharField(max_length=300)
    options = models.JSONField(default=list)  # 4 strings
    correct_option = models.IntegerField(default=0)  # 0=A 1=B 2=C 3=D

    class Meta:
        ordering = ["id"]


class Participant(models.Model):
    """Quien escaneo el QR antes de que empezara el evento."""

    uuid = models.CharField(max_length=64, unique=True)
    joined_at = models.DateTimeField(auto_now_add=True)


class State(models.Model):
    """Fila unica (pk=1): en que momento del evento estamos."""

    started = models.BooleanField(default=False)
    finished = models.BooleanField(default=False)


class Response(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="responses"
    )
    participant_uuid = models.CharField(max_length=64)
    selected_option = models.IntegerField()
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Una sola respuesta por persona por pregunta (lo garantiza SQLite).
        constraints = [
            models.UniqueConstraint(
                fields=["question", "participant_uuid"],
                name="una_respuesta_por_pregunta",
            )
        ]


def get_state():
    state, _ = State.objects.get_or_create(pk=1)
    return state


def ensure_seed():
    """Primera corrida: crea la pregunta de config/settings.py."""
    if not Question.objects.exists():
        Question.objects.create(
            text=settings.QUESTION,
            options=settings.OPTIONS,
            correct_option=settings.CORRECT_OPTION,
        )
