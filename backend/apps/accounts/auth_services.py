from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import TYPE_CHECKING

import pyotp
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError

from apps.core.audit import record_audit
from apps.core.models import AuditLog

from .authentication import mark_session_revoked
from .models import (
    AuthSession,
    EmailVerificationToken,
    PasswordResetToken,
    RecoveryCode,
    User,
)
from .passwords import validate_password_not_breached
from .tokens import (
    RefreshTokenReplay,
    create_access_token,
    create_auth_session,
    hash_token,
    new_refresh_token,
    refresh_token_lifetime,
)

if TYPE_CHECKING:
    from django.http import HttpRequest


def hash_ip(ip: str) -> str:
    return hashlib.sha256(f"{settings.SECRET_KEY}:{ip}".encode()).hexdigest()


def record_auth_audit(
    *,
    action: str,
    user: User | None = None,
    target_id: str = "unknown",
    after: dict[str, object] | None = None,
) -> None:
    if user is not None:
        record_audit(action=action, target=user, actor=user, after=after)
        return
    AuditLog.objects.create(
        actor_type="anonymous",
        action=action,
        target_type="authentication",
        target_id=target_id,
        after=after,
    )


def request_ip(request: HttpRequest) -> str:
    return request.META.get("REMOTE_ADDR", "")


def issue_token(raw_value: str, model, user: User, lifetime: timedelta):
    return model.objects.create(
        user=user,
        token_hash=hash_token(raw_value),
        expires_at=timezone.now() + lifetime,
    )


@transaction.atomic
def issue_verification_token(user: User) -> str:
    raw = secrets.token_urlsafe(40)
    issue_token(raw, EmailVerificationToken, user, timedelta(hours=24))
    return raw


@transaction.atomic
def confirm_verification(raw: str) -> User:
    try:
        token = (
            EmailVerificationToken.objects.select_for_update()
            .select_related("user")
            .get(
                token_hash=hash_token(raw),
            )
        )
    except EmailVerificationToken.DoesNotExist as exc:
        raise ValidationError({"token": ["Invalid verification token."]}) from exc
    if token.used_at or token.expires_at <= timezone.now():
        raise ValidationError({"token": ["Verification token is expired or already used."]})
    token.used_at = timezone.now()
    token.save(update_fields=["used_at", "updated_at"])
    user = token.user
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified", "updated_at"])
    record_audit(action="email_verified", target=user, actor=user)
    return user


@transaction.atomic
def issue_password_reset_token(user: User) -> str:
    raw = secrets.token_urlsafe(40)
    issue_token(raw, PasswordResetToken, user, timedelta(hours=1))
    return raw


@transaction.atomic
def reset_password(raw: str, password: str) -> User:
    try:
        token = (
            PasswordResetToken.objects.select_for_update()
            .select_related("user")
            .get(
                token_hash=hash_token(raw),
            )
        )
    except PasswordResetToken.DoesNotExist as exc:
        raise ValidationError({"token": ["Invalid password reset token."]}) from exc
    if token.used_at or token.expires_at <= timezone.now():
        raise ValidationError({"token": ["Password reset token is expired or already used."]})
    user = token.user
    validate_password(password, user)
    validate_password_not_breached(password, user)
    user.set_password(password)
    user.password_changed_at = timezone.now()
    user.save(update_fields=["password", "password_changed_at", "updated_at"])
    revoke_all_sessions(user, actor=user, reason="password_reset")
    token.used_at = timezone.now()
    token.save(update_fields=["used_at", "updated_at"])
    record_audit(action="password_reset", target=user, actor=user)
    return user


@transaction.atomic
def change_password(user: User, current_password: str, password: str) -> None:
    if not user.check_password(current_password):
        raise AuthenticationFailed("Current password is incorrect.")
    validate_password(password, user)
    validate_password_not_breached(password, user)
    user.set_password(password)
    user.password_changed_at = timezone.now()
    user.save(update_fields=["password", "password_changed_at", "updated_at"])
    revoke_all_sessions(user, actor=user, reason="password_change")
    record_audit(action="password_changed", target=user, actor=user)


@transaction.atomic
def revoke_session(session: AuthSession, *, actor=None, reason: str = "logout") -> None:
    session = AuthSession.objects.select_for_update().get(pk=session.pk)
    if session.revoked_at is None:
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at", "updated_at"])
        mark_session_revoked(str(session.pk))
        record_audit(
            action="session_revoked",
            target=session,
            actor=actor,
            after={"reason": reason},
        )


@transaction.atomic
def revoke_all_sessions(user: User, *, actor=None, reason: str = "logout_all") -> None:
    now = timezone.now()
    sessions = list(
        AuthSession.objects.select_for_update().filter(user=user, revoked_at__isnull=True)
    )
    AuthSession.objects.filter(pk__in=[session.pk for session in sessions]).update(
        revoked_at=now,
        updated_at=now,
    )
    for session in sessions:
        mark_session_revoked(str(session.pk))
    record_audit(
        action="sessions_revoked",
        target=user,
        actor=actor,
        after={"reason": reason, "count": len(sessions)},
    )


def rotate_refresh_token(raw: str, *, user_agent: str = "", ip_hash: str = ""):
    with transaction.atomic():
        try:
            session = (
                AuthSession.objects.select_for_update()
                .select_related("user")
                .get(
                    token_hash=hash_token(raw),
                )
            )
        except AuthSession.DoesNotExist as exc:
            raise AuthenticationFailed("Invalid refresh token.") from exc
        if (
            session.expires_at <= timezone.now()
            or session.revoked_at is not None
            or session.replaced_by_id is not None
        ):
            family = list(
                AuthSession.objects.select_for_update().filter(family_id=session.family_id)
            )
            now = timezone.now()
            for family_session in family:
                if family_session.revoked_at is None:
                    family_session.revoked_at = now
                    family_session.save(update_fields=["revoked_at", "updated_at"])
                mark_session_revoked(str(family_session.pk))
            record_audit(
                action="refresh_reuse_detected",
                target=session,
                actor=session.user,
                after={"family_id": str(session.family_id)},
            )
            replay = RefreshTokenReplay(session)
        else:
            new_raw = new_refresh_token()
            replacement = AuthSession.objects.create(
                user=session.user,
                family_id=session.family_id,
                token_hash=hash_token(new_raw),
                user_agent=user_agent[:1000],
                ip_hash=ip_hash,
                expires_at=timezone.now() + refresh_token_lifetime(),
                last_used_at=timezone.now(),
            )
            session.replaced_by = replacement
            session.last_used_at = timezone.now()
            session.save(update_fields=["replaced_by", "last_used_at", "updated_at"])
            return replacement, new_raw
    raise replay


def issue_tokens(user: User, *, user_agent: str = "", ip_hash: str = "") -> dict[str, str]:
    session, refresh = create_auth_session(user=user, user_agent=user_agent, ip_hash=ip_hash)
    return {
        "access": create_access_token(session, user),
        "refresh": refresh,
        "session_id": str(session.pk),
    }


def setup_totp(user: User) -> str:
    if user.totp_enabled:
        raise ValidationError({"totp": ["Two-factor authentication is already enabled."]})
    secret = pyotp.random_base32()
    user.totp_pending_secret = secret
    user.save(update_fields=["totp_pending_secret", "updated_at"])
    return pyotp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name=settings.TOTP_ISSUER,
    )


def _totp_valid(user: User, code: str) -> bool:
    if not user.totp_secret:
        return False
    now = timezone.now()
    step = int(now.timestamp()) // 30
    if user.totp_last_step is not None and step <= user.totp_last_step:
        return False
    return pyotp.TOTP(user.totp_secret).verify(code, for_time=now, valid_window=0)


@transaction.atomic
def confirm_totp(user: User, code: str) -> list[str]:
    user = User.objects.select_for_update().get(pk=user.pk)
    if not user.totp_pending_secret:
        raise ValidationError({"totp": ["Start TOTP setup first."]})
    now = timezone.now()
    if not pyotp.TOTP(user.totp_pending_secret).verify(code, for_time=now, valid_window=0):
        raise ValidationError({"code": ["Invalid authenticator code."]})
    user.totp_secret = user.totp_pending_secret
    user.totp_pending_secret = ""
    user.totp_enabled = True
    user.totp_last_step = int(now.timestamp()) // 30
    user.save(
        update_fields=[
            "totp_secret",
            "totp_pending_secret",
            "totp_enabled",
            "totp_last_step",
            "updated_at",
        ]
    )
    codes = regenerate_recovery_codes(user)
    record_audit(action="two_factor_enabled", target=user, actor=user)
    return codes


@transaction.atomic
def verify_totp_or_recovery(user: User, code: str) -> bool:
    user = User.objects.select_for_update().get(pk=user.pk)
    if _totp_valid(user, code):
        now = timezone.now()
        user.totp_last_step = int(now.timestamp()) // 30
        user.save(update_fields=["totp_last_step", "updated_at"])
        return True
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    recovery = (
        RecoveryCode.objects.select_for_update()
        .filter(user=user, code_hash=code_hash, used_at__isnull=True)
        .first()
    )
    if recovery is None:
        return False
    recovery.used_at = timezone.now()
    recovery.save(update_fields=["used_at", "updated_at"])
    record_audit(action="recovery_code_used", target=user, actor=user)
    return True


@transaction.atomic
def disable_totp(user: User, code: str) -> None:
    if user.is_staff:
        raise PermissionDenied("Staff accounts must retain two-factor authentication.")
    if not verify_totp_or_recovery(user, code):
        raise ValidationError({"code": ["Invalid authenticator code."]})
    user.totp_secret = ""
    user.totp_pending_secret = ""
    user.totp_enabled = False
    user.totp_last_step = None
    user.save(
        update_fields=[
            "totp_secret",
            "totp_pending_secret",
            "totp_enabled",
            "totp_last_step",
            "updated_at",
        ]
    )
    RecoveryCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    record_audit(action="two_factor_disabled", target=user, actor=user)


def regenerate_recovery_codes(user: User) -> list[str]:
    RecoveryCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    codes: list[str] = []
    for _ in range(10):
        raw = secrets.token_urlsafe(9)
        codes.append(raw)
        RecoveryCode.objects.create(
            user=user,
            code_hash=hashlib.sha256(raw.encode()).hexdigest(),
        )
    record_audit(action="recovery_codes_regenerated", target=user, actor=user)
    return codes
