from __future__ import annotations

import secrets
from typing import cast

from django.conf import settings
from django.contrib.auth import authenticate
from django.middleware.csrf import _does_token_match, get_token  # type: ignore[attr-defined]
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, Throttled
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.auth_serializers import (
    LoginChallengeSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SessionSerializer,
    SignupSerializer,
    TokenSerializer,
    TotpCodeSerializer,
    UserResponseSerializer,
    VerificationSerializer,
)
from apps.core.views import NonTenantView, PublicReadOnlyView

from .auth_services import (
    change_password,
    confirm_totp,
    confirm_verification,
    disable_totp,
    hash_ip,
    issue_password_reset_token,
    issue_tokens,
    issue_verification_token,
    record_auth_audit,
    regenerate_recovery_codes,
    request_ip,
    reset_password,
    revoke_all_sessions,
    revoke_session,
    rotate_refresh_token,
    setup_totp,
    verify_totp_or_recovery,
)
from .models import AuthSession, User
from .throttling import ThrottleState, clear, get_state, key, record_failure
from .tokens import RefreshTokenReplay, create_access_token

REFRESH_COOKIE = "portfolio_refresh"
CHALLENGE_TTL = 300


class PublicAuthView(PublicReadOnlyView, APIView):  # type: ignore[misc]
    pass


class AuthenticatedAuthView(NonTenantView, APIView):
    permission_classes = [IsAuthenticated]


def csrf_check(request) -> None:
    cookie = request.COOKIES.get(settings.CSRF_COOKIE_NAME)
    header = request.META.get("HTTP_X_CSRFTOKEN")
    if not cookie or not header or not _does_token_match(header, cookie):
        raise PermissionDenied("CSRF verification failed.")


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=30 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="Strict",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, samesite="Strict")


def _issue_response(user: User, request) -> Response:
    token_data = issue_tokens(
        user,
        user_agent=request.headers.get("User-Agent", ""),
        ip_hash=hash_ip(request_ip(request)),
    )
    response = Response(
        {
            **TokenSerializer(token_data).data,
            "user": UserResponseSerializer(user).data,
        }
    )
    set_refresh_cookie(response, token_data["refresh"])
    record_auth_audit(action="login_success", user=user)
    return response


def _throttle_keys(request, email: str) -> tuple[str, str]:
    return key("ip", hash_ip(request_ip(request))), key("account", email.lower())


def _locked(keys: tuple[str, str]) -> bool:
    return any(get_state(identifier).locked_until for identifier in keys)


def _record_login_failure(user: User | None, request, email: str) -> ThrottleState:
    states = [record_failure(identifier) for identifier in _throttle_keys(request, email)]
    state = max(states, key=lambda item: item.count)
    if user is not None:
        record_auth_audit(action="login_failure", user=user)
    else:
        record_auth_audit(action="login_failure", target_id=email)
    if state.locked_until is not None:
        if user is not None:
            record_auth_audit(
                action="login_lockout",
                user=user,
                after={"locked_until": state.locked_until.isoformat()},
            )
            from apps.notifications.services import queue_email

            queue_email(
                to_email=user.email,
                template_code="login_lockout",
                context={
                    "subject": "Your Portfolio CMS account is locked",
                    "body": "Too many failed login attempts were detected.",
                },
                related_object_ref=f"login-lockout:{user.pk}:{state.count}",
            )
    return state


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(PublicAuthView):
    serializer_class = None

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


class SignupView(PublicAuthView):
    serializer_class = SignupSerializer

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from .services import signup

        user, account, _membership, _portfolio, _subscription = signup(**serializer.validated_data)
        raw = issue_verification_token(user)
        from apps.notifications.services import queue_email

        queue_email(
            to_email=user.email,
            template_code="email_verification",
            context={
                "subject": "Verify your Portfolio CMS email",
                "body": f"Use this verification token: {raw}",
            },
            related_object_ref=f"verification:{user.pk}",
        )
        return Response(
            {
                "user": UserResponseSerializer(user).data,
                "account_id": account.id,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(PublicAuthView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        keys = _throttle_keys(request, email)
        if _locked(keys):
            raise Throttled(detail="Login temporarily locked.")
        user = cast(
            User | None,
            authenticate(
                request,
                username=email,
                password=serializer.validated_data["password"],
            ),
        )
        if user is None:
            _record_login_failure(User.objects.filter(email=email).first(), request, email)
            raise AuthenticationFailed("Invalid email or password.")
        state = _record_login_failure(user, request, email) if not user.is_active else None
        if state and state.locked_until:
            raise Throttled(detail="Login temporarily locked.")
        if user.is_staff and not user.totp_enabled:
            raise PermissionDenied("Staff accounts require two-factor authentication.")
        clear(keys[0])
        clear(keys[1])
        if user.totp_enabled:
            challenge_id = secrets.token_urlsafe(32)
            from django.core.cache import cache

            cache.set(
                f"auth:challenge:{challenge_id}",
                {
                    "user_id": str(user.pk),
                    "user_agent": request.headers.get("User-Agent", ""),
                    "ip_hash": hash_ip(request_ip(request)),
                },
                CHALLENGE_TTL,
            )
            return Response({"requires_2fa": True, "challenge_id": challenge_id})
        return _issue_response(user, request)


class LoginTwoFactorView(PublicAuthView):
    serializer_class = LoginChallengeSerializer

    def post(self, request):
        serializer = LoginChallengeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from django.core.cache import cache

        challenge_key = f"auth:challenge:{serializer.validated_data['challenge_id']}"
        challenge = cache.get(challenge_key)
        if not isinstance(challenge, dict):
            raise AuthenticationFailed("Invalid or expired authentication challenge.")
        try:
            user = User.objects.get(pk=challenge["user_id"])
        except User.DoesNotExist as exc:
            raise AuthenticationFailed("Invalid authentication challenge.") from exc
        if not verify_totp_or_recovery(user, serializer.validated_data["code"]):
            raise AuthenticationFailed("Invalid authenticator code.")
        cache.delete(challenge_key)
        return _issue_response(user, request)


class RefreshView(PublicAuthView):
    serializer_class = None

    def post(self, request):
        csrf_check(request)
        raw = request.COOKIES.get(REFRESH_COOKIE)
        if not raw:
            raise AuthenticationFailed("Refresh token is required.")
        try:
            session, replacement = rotate_refresh_token(
                raw,
                user_agent=request.headers.get("User-Agent", ""),
                ip_hash=hash_ip(request_ip(request)),
            )
        except RefreshTokenReplay as exc:
            raise AuthenticationFailed("Refresh token reuse detected.") from exc
        response = Response(
            {
                "access": create_access_token(session, session.user),
                "session_id": session.pk,
            }
        )
        set_refresh_cookie(response, replacement)
        return response


class LogoutView(AuthenticatedAuthView):
    serializer_class = None

    def post(self, request):
        csrf_check(request)
        session_id = str(request.auth.get("sid"))
        session = AuthSession.objects.filter(pk=session_id, user=request.user).first()
        if session is not None:
            revoke_session(session, actor=request.user)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        record_auth_audit(action="logout", user=request.user)
        return response


class LogoutAllView(AuthenticatedAuthView):
    serializer_class = None

    def post(self, request):
        csrf_check(request)
        revoke_all_sessions(request.user, actor=request.user)
        record_auth_audit(action="logout_all", user=request.user)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response


class SessionListView(AuthenticatedAuthView):
    serializer_class = SessionSerializer

    def get(self, request):
        sessions = AuthSession.objects.filter(user=request.user).order_by("-created_at")
        return Response(SessionSerializer(sessions, many=True).data)


class SessionRevokeView(AuthenticatedAuthView):
    serializer_class = None

    def post(self, request, session_id):
        session = AuthSession.objects.filter(user=request.user, pk=session_id).first()
        if session is None:
            raise PermissionDenied
        revoke_session(session, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerificationRequestView(PublicAuthView):
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        email = str(request.data.get("email", "")).lower()
        user = User.objects.filter(email=email).first()
        if user is not None and not user.is_email_verified:
            raw = issue_verification_token(user)
            from apps.notifications.services import queue_email

            queue_email(
                to_email=user.email,
                template_code="email_verification",
                context={
                    "subject": "Verify your Portfolio CMS email",
                    "body": f"Use this verification token: {raw}",
                },
                related_object_ref=f"verification:{user.pk}",
            )
        return Response({"detail": "If the account exists, a verification email was queued."})


class VerificationConfirmView(PublicAuthView):
    serializer_class = VerificationSerializer

    def post(self, request):
        serializer = VerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = confirm_verification(serializer.validated_data["token"])
        return Response(UserResponseSerializer(user).data)


class PasswordChangeView(AuthenticatedAuthView):
    serializer_class = PasswordChangeSerializer

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        change_password(request.user, **serializer.validated_data)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response


class PasswordResetRequestView(PublicAuthView):
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"].lower()).first()
        if user is not None:
            raw = issue_password_reset_token(user)
            from apps.notifications.services import queue_email

            queue_email(
                to_email=user.email,
                template_code="password_reset",
                context={
                    "subject": "Reset your Portfolio CMS password",
                    "body": f"Use this password reset token: {raw}",
                },
                related_object_ref=f"password-reset:{user.pk}",
            )
        return Response({"detail": "If the account exists, a reset email was queued."})


class PasswordResetConfirmView(PublicAuthView):
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = reset_password(
            raw=serializer.validated_data["token"],
            password=serializer.validated_data["password"],
        )
        return Response(UserResponseSerializer(user).data)


class TotpSetupView(AuthenticatedAuthView):
    serializer_class = None

    def post(self, request):
        return Response({"provisioning_uri": setup_totp(request.user)})


class TotpConfirmView(AuthenticatedAuthView):
    serializer_class = TotpCodeSerializer

    def post(self, request):
        serializer = TotpCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {"recovery_codes": confirm_totp(request.user, serializer.validated_data["code"])}
        )


class TotpDisableView(AuthenticatedAuthView):
    serializer_class = TotpCodeSerializer

    def post(self, request):
        serializer = TotpCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        disable_totp(request.user, serializer.validated_data["code"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecoveryCodesRegenerateView(AuthenticatedAuthView):
    serializer_class = TotpCodeSerializer

    def post(self, request):
        serializer = TotpCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not verify_totp_or_recovery(request.user, serializer.validated_data["code"]):
            raise AuthenticationFailed("Invalid authenticator code.")
        return Response({"recovery_codes": regenerate_recovery_codes(request.user)})
