"""
Local development settings. Uses .env file for secrets.
design_doc §7.1 — local Docker Compose environment
"""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Override: allow all origins for local API testing with Postman / React dev server
CORS_ALLOW_ALL_ORIGINS = True
