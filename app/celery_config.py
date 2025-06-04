# app/celery_config.py
# import eventlet
# eventlet.monkey_patch()

from celery import Celery
from celery.schedules import crontab
from app.config import settings
import redis

WS_MESSAGE_CHANNEL = settings.WS_MESSAGE_CHANNEL

try:
    redis_client_for_celery_config = redis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
    redis_client_for_celery_config.ping()
    print(f"INFO:     Successfully connected to Redis for Celery config and Pub/Sub: {settings.CELERY_BROKER_URL}")
except redis.exceptions.ConnectionError as e:
    print(f"ERROR:    Could not connect to Redis for Celery config and Pub/Sub: {settings.CELERY_BROKER_URL}. Error: {e}")
    redis_client_for_celery_config = None


celery_app = Celery(
    'kindergarten_celery_tasks',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'app.tasks.portion_tasks',
        'app.tasks.report_tasks',
    ]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone=settings.TIMEZONE,
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Davriy vazifalar (Celery Beat) uchun sozlamalar
# Celery Beat workerni alohida ishga tushirish kerak bo'ladi.
celery_app.conf.beat_schedule = {
    'generate-monthly-report-schedule': {
        'task': 'app.tasks.report_tasks.task_schedule_previous_month_report_generation',
        'schedule': crontab(day_of_month='1', hour=3, minute=0), # Har oyning 1-kuni soat 03:00 da
        'options': {'queue': 'reports_queue'}
    },
    'recalculate-possible-portions-schedule': {
        'task': 'app.tasks.portion_tasks.task_update_all_possible_meal_portions_celery',
        'schedule': crontab(minute='*/30'),
        'options': {'queue': 'portions_queue'}
    },
}

# celery -A app.celery_config.celery_app worker -l info -P eventlet
# (Windows uchun `-P solo` yoki `-P gevent` (agar o'rnatilgan bo'lsa))

# Celery Beatni ishga tushirish uchun buyruq:
# celery -A app.celery_config.celery_app beat -l info --scheduler celery.beat:PersistentScheduler
# Yoki oddiyroq: celery -A app.celery_config.celery_app beat -l info