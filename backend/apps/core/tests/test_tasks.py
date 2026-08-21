from apps.core.tasks import CorrelatedTask, maintenance_heartbeat


def test_celery_task_defaults_and_idle_task():
    assert CorrelatedTask.retry_backoff is True
    assert CorrelatedTask.reject_on_worker_lost is True
    assert Exception not in CorrelatedTask.autoretry_for
    assert maintenance_heartbeat.apply().successful()
