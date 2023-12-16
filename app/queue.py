from celery import Celery
from app.config import REDIS_URL

celery = Celery("app", broker=REDIS_URL, include=["app.tasks"])

celery.conf.worker_pool_restarts = True
celery.conf.broker_connection_retry_on_startup = True
celery.conf.result_expires = 60
