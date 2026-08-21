from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings
from django.utils import timezone

from .models import AuthSession, User


def access_token_lifetime() -> timedelta:
    return timedelta(seconds=settings.AUTH_ACCESS_TOKEN_LIFETIME_SECONDS)


def refresh_token_lifetime() -> timedelta:
    return timedelta(days=settings.AUTH_REFRESH_TOKEN_LIFETIME_DAYS)


class InvalidAccessToken(Exception):
    pass


class RefreshTokenReplay(Exception):
    def __init__(self, session: AuthSession):
        self.session = session


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(session: AuthSession, user: User) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user.pk),
            "sid": str(session.pk),
            "iat": now,
            "exp": now + access_token_lifetime(),
            "iss": settings.AUTH_JWT_ISSUER,
            "type": "access",
        },
        settings.AUTH_JWT_SIGNING_KEY,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> dict[str, object]:
    try:
        claims = jwt.decode(
            token,
            settings.AUTH_JWT_SIGNING_KEY,
            algorithms=["HS256"],
            issuer=settings.AUTH_JWT_ISSUER,
            options={"require": ["sub", "sid", "iat", "exp", "iss", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidAccessToken from exc
    if claims.get("type") != "access":
        raise InvalidAccessToken
    return claims


def create_auth_session(
    *,
    user: User,
    user_agent: str = "",
    ip_hash: str = "",
) -> tuple[AuthSession, str]:
    raw_token = new_refresh_token()
    session = AuthSession.objects.create(
        user=user,
        family_id=uuid.uuid4(),
        token_hash=hash_token(raw_token),
        user_agent=user_agent[:1000],
        ip_hash=ip_hash,
        expires_at=timezone.now() + refresh_token_lifetime(),
        last_used_at=timezone.now(),
    )
    return session, raw_token
