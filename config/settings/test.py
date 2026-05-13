"""
Test settings — design_doc §9.4 pytest configuration.
Phase 2 will add CELERY_TASK_ALWAYS_EAGER and LLM_PROVIDER=mock.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "test_diagnosis_db",
        "USER": "user",
        "PASSWORD": "pass",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

# Speed up tests — no real password hashing overhead
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
