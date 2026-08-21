from __future__ import annotations

from typing import Protocol

from django.conf import settings
from django.core.mail import EmailMessage as DjangoEmailMessage


class EmailProvider(Protocol):
    def send(
        self,
        *,
        to_email: str,
        template_code: str,
        context: dict[str, object],
    ) -> str: ...


class DjangoEmailProvider:
    def send(
        self,
        *,
        to_email: str,
        template_code: str,
        context: dict[str, object],
    ) -> str:
        subject = str(context.get("subject", "Portfolio CMS notification"))
        body = str(context.get("body", ""))
        message = DjangoEmailMessage(
            subject=subject,
            body=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
            to=[to_email],
        )
        message.send(fail_silently=False)
        return ""
