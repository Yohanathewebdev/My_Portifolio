from __future__ import annotations

from celery import shared_task

from apps.core.tasks import CorrelatedTask

from .models import EmailMessage
from .providers import DjangoEmailProvider


@shared_task(base=CorrelatedTask, name="apps.notifications.tasks.send_email_message", queue="email")
def send_email_message(message_id: str) -> None:
    message = EmailMessage.objects.get(pk=message_id)
    if message.status == EmailMessage.STATUS_SENT:
        return
    try:
        provider_id = DjangoEmailProvider().send(
            to_email=message.to_email,
            template_code=message.template_code,
            context=message.context,
        )
    except Exception as exc:
        message.status = EmailMessage.STATUS_FAILED
        message.error = str(exc)
        message.save(update_fields=["status", "error", "updated_at"])
        raise
    message.status = EmailMessage.STATUS_SENT
    message.provider_message_id = provider_id
    message.save(update_fields=["status", "provider_message_id", "updated_at"])
