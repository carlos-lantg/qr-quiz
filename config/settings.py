import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "conferencia-una-sola-vez-no-importa")
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o
]

# ---------------------------------------------------------------------------
# LA PREGUNTA (editar aqui o via variables de entorno)
# ---------------------------------------------------------------------------
QUESTION = os.environ.get("QUESTION", "¿Cuál es la capital de República Dominicana?")
OPTIONS = [
    os.environ.get("OPTION_A", "Santiago"),
    os.environ.get("OPTION_B", "Santo Domingo"),
    os.environ.get("OPTION_C", "La Romana"),
    os.environ.get("OPTION_D", "Puerto Plata"),
]
# Indice de la respuesta correcta: 0=A, 1=B, 2=C, 3=D
CORRECT_OPTION = int(os.environ.get("CORRECT_OPTION", "1"))

# URL publica que se codifica en el QR. Si esta vacia se arma con el host actual.
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "quiz",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {},
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# DB_PATH permite apuntar el SQLite a un disco persistente (Render Disk).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DB_PATH") or BASE_DIR / "db.sqlite3",
    }
}

# Render termina el TLS en su proxy: sin esto el QR se generaria con http://
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LANGUAGE_CODE = "es"
TIME_ZONE = os.environ.get("TIME_ZONE", "America/Santo_Domingo")
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
