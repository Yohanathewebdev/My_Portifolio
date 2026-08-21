from __future__ import annotations

import logging
from typing import cast

from django.core.cache import cache
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from .models import AuthSession, User
from .tokens import InvalidAccessToken, decode_access_token

logger = logging.getLogger("portfolio.authentication")
REVOCATION_CACHE_TTL = 15 * 60


def revocation_cache_key(session_id: str) -> str:
    return f"auth:revoked:{session_id}"


def mark_session_revoked(session_id: str) -> None:
    try:
        cache.set(revocation_cache_key(session_id), True, REVOCATION_CACHE_TTL)
    except Exception:
        logger.exception("auth_revocation_cache_unavailable", extra={"session_id": session_id})


class AccessTokenAuthentication(BaseAuthentication):
    def authenticate(self, request: Request):
        header = get_authorization_header(request).split()
        if not header:
            return None
        if header[0].lower() != b"bearer" or len(header) != 2:
            raise AuthenticationFailed("Invalid authorization header.")
        try:
            claims = decode_access_token(header[1].decode("ascii"))
        except (UnicodeDecodeError, InvalidAccessToken) as exc:
            raise AuthenticationFailed("Invalid access token.") from exc

        session_id = str(claims["sid"])
        user_id = str(claims["sub"])
        try:
            revoked = cache.get(revocation_cache_key(session_id))
        except Exception:
            # Fail open on cache outages: the access token is bounded to 15 minutes.
            logger.exception(
                "auth_revocation_cache_unavailable_fail_open",
                extra={"session_id": session_id},
            )
            revoked = False
            cache_unavailable = True
        else:
            cache_unavailable = False
        if revoked:
            raise AuthenticationFailed("Session has been revoked.")
        try:
            session = AuthSession.objects.select_related("user").get(
                pk=session_id,
                user_id=user_id,
            )
        except AuthSession.DoesNotExist as exc:
            raise AuthenticationFailed("Session is not valid.") from exc
        if session.revoked_at is not None:
            if not cache_unavailable:
                mark_session_revoked(session_id)
            raise AuthenticationFailed("Session has been revoked.")
        user = cast(User, session.user)
        if not user.is_active:
            raise AuthenticationFailed("User is inactive.")
        return user, claims

    def authenticate_header(self, request: Request) -> str:
        return "Bearer"
