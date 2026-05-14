"""
Celery application — design_doc §6
Broker: Redis (local dev), AWS SQS (production via Lambda).
Tasks auto-discovered from all installed apps and the top-level tasks/ package.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("config")

# Read Celery config from Django settings using the CELERY_ namespace prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Task modules are imported via CELERY_IMPORTS in settings (mapped to Celery's
# `imports` config by the CELERY_ namespace prefix). autodiscover_tasks(["tasks"])
# would look for tasks.tasks which does not exist in this project structure.
app.autodiscover_tasks()
