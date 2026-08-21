from __future__ import annotations

from .models import EmailMessage
from .tasks import send_email_message


def queue_email(
    *,
    to_email: str,
    template_code: str,
    context: dict[str, object],
    related_object_ref: str,
) -> EmailMessage:
    message, _ = EmailMessage.objects.get_or_create(
        to_email=to_email,
        template_code=template_code,
        related_object_ref=related_object_ref,
        defaults={"context": context},
    )
    if message.status != EmailMessage.STATUS_SENT:
        send_email_message.delay(str(message.pk))
    return message
