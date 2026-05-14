"""
Base settings shared across all environments.
design_doc §3 Tech Stack — Django 4.2, DRF, simplejwt, PostgreSQL 15
"""
from datetime import timedelta
from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="dev-insecure-key-override-in-production")

DEBUG = False

ALLOWED_HOSTS = []

# design_doc §3 — INSTALLED_APPS includes django.contrib.postgres for ArrayField
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",       # required for ArrayField (symptoms, existing_conditions)
    "rest_framework",
    "rest_framework_simplejwt",
    "apps.authentication",
    "apps.patients",
    "apps.diagnosis",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# design_doc §5.1 — PostgreSQL 15
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="diagnosis_db"),
        "USER": config("DB_USER", default="user"),
        "PASSWORD": config("DB_PASSWORD", default="pass"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

# design_doc §1 — custom User model with role field
AUTH_USER_MODEL = "authentication.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# design_doc §4 — JWT auth, custom exception handler, pagination (page_size=20)
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "EXCEPTION_HANDLER": "config.exception_handler.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# design_doc §4.1 — access 1h, refresh 7d
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ── Celery — design_doc §6 ─────────────────────────────────────────────────
CELERY_BROKER_URL = config("REDIS_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://redis:6379/0")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_TRACK_STARTED = True
# Explicitly import top-level tasks/ package on worker startup.
# autodiscover_tasks(["tasks"]) looks for tasks.tasks — wrong package structure.
CELERY_IMPORTS = ("tasks.llm_task", "tasks.pdf_task")

# ── Duplicate detection windows — design_doc §4.3 ─────────────────────────
# Set to small values (e.g. 0.01 = ~36s) in .env to test all three scenarios
# without waiting. Production keeps defaults: 1h hard error, 24h soft warning.
DUPLICATE_HARD_ERROR_HOURS = config("DUPLICATE_HARD_ERROR_HOURS", default=1.0, cast=float)
DUPLICATE_SOFT_WARN_HOURS  = config("DUPLICATE_SOFT_WARN_HOURS",  default=24.0, cast=float)

# ── LLM Adapter — design_doc §6 ───────────────────────────────────────────
# LLM_PROVIDER: "claude" | "openai" | "mock"
# "mock" returns a fixed JSON response — safe default for dev/test
LLM_PROVIDER = config("LLM_PROVIDER", default="mock")
CLAUDE_API_KEY = config("CLAUDE_API_KEY", default="")
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")

# ── AWS S3 — design_doc §2 (PDF report storage) ───────────────────────────
# Leave AWS_S3_BUCKET_NAME empty → S3Adapter falls back to local filesystem
AWS_S3_BUCKET_NAME = config("AWS_S3_BUCKET_NAME", default="")
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_DEFAULT_REGION = config("AWS_DEFAULT_REGION", default="us-east-1")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
