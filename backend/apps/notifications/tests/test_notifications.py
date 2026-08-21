import pytest
from django.core import mail

from apps.notifications.models import EmailMessage
from apps.notifications.services import queue_email


@pytest.mark.django_db
def test_email_queue_is_idempotent_and_sends_once():
    first = queue_email(
        to_email="person@example.com",
        template_code="verification",
        context={"subject": "Verify", "body": "token"},
        related_object_ref="user:1",
    )
    second = queue_email(
        to_email="person@example.com",
        template_code="verification",
        context={"subject": "Verify", "body": "token"},
        related_object_ref="user:1",
    )
    assert first.pk == second.pk
    assert EmailMessage.objects.count() == 1
    assert EmailMessage.objects.get().status == EmailMessage.STATUS_SENT
    assert len(mail.outbox) == 1
