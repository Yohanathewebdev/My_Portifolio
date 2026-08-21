from unittest.mock import patch

import pytest
from django.core import mail
from django.db import transaction

from apps.notifications.models import EmailMessage
from apps.notifications.services import queue_email


@pytest.mark.django_db
def test_email_queue_is_idempotent_and_sends_once(django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
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


@pytest.mark.django_db
def test_email_dispatch_waits_for_transaction_commit(django_capture_on_commit_callbacks):
    with patch("apps.notifications.services.send_email_message.delay") as delay:
        with django_capture_on_commit_callbacks(execute=True):
            with transaction.atomic():
                message = queue_email(
                    to_email="commit@example.com",
                    template_code="verification",
                    context={"subject": "Verify", "body": "token"},
                    related_object_ref="token:commit",
                )
                delay.assert_not_called()
        delay.assert_called_once_with(str(message.pk))
