import os

from celery import Celery

from relay.transport import dispatch
from relay.worker import process

app = Celery("relay", broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"))
app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=50,
    task_time_limit=60,
    beat_schedule={"publish-outbox": {"task": "relay.dispatch", "schedule": 3.0}},
)


@app.task(
    name="relay.analyse",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=8,
)
def analyse_incident(event):
    return process(event)


@app.task(name="relay.dispatch")
def publish_outbox():
    return dispatch()
