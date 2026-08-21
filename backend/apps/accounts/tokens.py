from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings
from django.utils import timezone

from .models import AuthSession, User

ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
REFRESH_TOKEN_LIFETIME = timedelta(days=30)


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
            "exp": now + ACCESS_TOKEN_LIFETIME,
            "type": "access",
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> dict[str, object]:
    try:
        claims = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["sub", "sid", "iat", "exp", "type"]},
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
        expires_at=timezone.now() + REFRESH_TOKEN_LIFETIME,
        last_used_at=timezone.now(),
    )
    return session, raw_token
