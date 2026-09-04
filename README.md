# QR Quiz — una pregunta, una conferencia

## Configurar la pregunta

Entrar a `/admin/` con la clave **123456**: ahí se agregan, editan y borran
preguntas (texto, 4 opciones y cuál es la correcta). Se guardan en la base.

Los valores de `config/settings.py` (o las variables de entorno de abajo) solo
son la **semilla**: crean la primera pregunta si la base está vacía.

```bash
export QUESTION="¿Cuál es la capital de República Dominicana?"
export OPTION_A="Santiago"
export OPTION_B="Santo Domingo"
export OPTION_C="La Romana"
export OPTION_D="Puerto Plata"
export CORRECT_OPTION=1   # 0=A 1=B 2=C 3=D
```

## Correr

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 0.0.0.0:8000
```

- Proyector: `http://<ip-de-tu-laptop>:8000/`
- El QR apunta al host con el que abriste el dashboard. Si usas un túnel
  (ngrok, Cloudflare Tunnel), fija la URL pública:
  `export BASE_URL="https://xxxx.ngrok-free.app"`

Misma wifi: usa tu IP local (`ipconfig getifaddr en0`) y abre el dashboard en
`http://<esa-ip>:8000/` para que el QR la codifique.

## Logo y colores

El logo es `logo.jpg` en la raíz del proyecto, servido en `/logo.jpg` por una
vista de 3 líneas (nada de `staticfiles`, así funciona con `DEBUG=0`). Para
cambiarlo, reemplaza el archivo: se muestra con `mix-blend-mode: multiply`, así
que el fondo blanco del logo se funde con el crema de la página.

La paleta sale del logo y está en `quiz/templates/_theme.html`
(`--gold #BE8B3C`, `--teal #4FB0A6`, `--teal-dark #166B6B`, fondo `#F7F4EE`).

## Cómo se corre el evento

1. Abre `/` en el proyector: **logo a la izquierda, QR a la derecha**, con el
   contador **N conectados**. Todavía no se ven ni preguntas ni marcador.
2. La gente escanea; en su teléfono ven *"Estás dentro ✓ Espera a que comience"*.
3. Presionas **Comenzar**: la pantalla cambia a **marcador + preguntas a la
   izquierda y logo a la derecha**. El QR desaparece, el grupo queda cerrado
   (quien escanee después ve *"El quiz ya comenzó"*) y a los conectados les
   aparecen las preguntas en el teléfono.
4. Cuando **todos** los participantes conectados responden **todas** las
   preguntas: confeti en el proyector y confeti + *"¡Terminó!"* en cada
   teléfono.
5. Si alguien se conectó y se fue, el quiz nunca llega al 100%: usa el botón
   **Terminar ahora** del dashboard para forzar el final y el confeti.

Para volver a empezar: **Reiniciar evento** en `/admin/` (borra respuestas y
participantes, y reabre el QR).

## Deploy en Render.com

El repo trae `render.yaml`, así que en Render: **New → Blueprint** → elige este
repo → Apply. O manualmente, **New → Web Service** con:

- Build command: `pip install -r requirements.txt`
- Start command: `python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
- Variables: `DEBUG=0`, `SECRET_KEY` (genera una), `ADMIN_PASSWORD` (la clave de
  `/admin/`, por defecto `123456`)

El QR se arma solo con el dominio de Render (`https://…onrender.com/answer/`),
no hay que configurar `BASE_URL`.

### Aviso importante: SQLite en el plan free se borra

El disco de Render es efímero. Cada deploy o reinicio deja la base en blanco, y
el plan free **suspende el servicio tras 15 minutos sin tráfico**: al despertar,
las preguntas que hayas cargado en `/admin/` y las respuestas ya no están.

Para la conferencia:

- Carga las preguntas en `/admin/` **poco antes** de empezar, no el día anterior.
- Ten el dashboard abierto: hace polling cada 2s y eso mantiene el servicio
  despierto durante todo el evento.
- Si quieres que sobreviva a reinicios: instancia de pago + **Disk** montado en
  `/var/data` y la variable `DB_PATH=/var/data/db.sqlite3`.

## Endpoints

| Ruta | Qué hace |
|---|---|
| `GET /` | Dashboard proyector + QR (polling cada 2s) |
| `GET /answer/` | Formulario móvil |
| `POST /api/answer/` | `{"uuid": "...", "question": id, "option": 0-3}` → 200 / 409 duplicado |
| `GET /api/stats/` | Totales globales + `questions[]` con el detalle por pregunta |
| `POST /api/join/` | `{"uuid": "..."}` → registra al participante; 403 si ya comenzó |
| `POST /api/start/` | Botón Comenzar: cierra el QR y abre las preguntas |
| `POST /api/finish/` | Botón Terminar ahora: fuerza el final |
| `GET/POST /admin/` | Agregar/editar/borrar preguntas + reiniciar evento (`123456`) |

El móvil muestra todas las preguntas en una sola página; cada una se responde
una sola vez por navegador (UUID en `localStorage` + `UNIQUE (question,
participant_uuid)` en SQLite).

`/api/start/` y `/api/finish/` no piden clave (el dashboard del proyector no
está logueado). Si alguien conoce la URL puede dispararlos; para el evento no
compartas la URL raíz, solo el QR de `/answer/`.

El participante **no** ve si acertó: solo "respuesta registrada". Los aciertos
se ven únicamente en el dashboard del proyector: marcador global grande arriba
y, debajo, una barra pequeña por pregunta. Si agregas o borras preguntas en
`/admin/`, el dashboard se recarga solo en el siguiente polling.

## Borrar respuestas antes del evento

Botón "Borrar todas las respuestas" en `/admin/`, o a lo bruto:

```bash
rm db.sqlite3 && .venv/bin/python manage.py migrate
```

(La clave del admin está hardcodeada en `quiz/views.py`: `ADMIN_PASSWORD`.)
