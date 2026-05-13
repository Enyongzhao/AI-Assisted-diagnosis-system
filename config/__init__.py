# Make Celery app available when Django starts — design_doc §6
from .celery import app as celery_app

__all__ = ("celery_app",)
