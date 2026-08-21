from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import patch

import jwt
import pyotp
import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from apps.accounts.auth_services import (
    confirm_totp,
    confirm_verification,
    hash_ip,
    issue_password_reset_token,
    issue_tokens,
    issue_verification_token,
    request_ip,
    reset_password,
    revoke_session,
    rotate_refresh_token,
    setup_totp,
    verify_totp_or_recovery,
)
from apps.accounts.authentication import AccessTokenAuthentication, mark_session_revoked
from apps.accounts.factories import AccountFactory, MembershipFactory, UserFactory
from apps.accounts.models import Account, AuthSession, RecoveryCode, User
from apps.accounts.throttling import get_state, key
from apps.accounts.tokens import (
    InvalidAccessToken,
    RefreshTokenReplay,
    create_auth_session,
    decode_access_token,
)
from apps.notifications.models import EmailMessage
from apps.portfolios.models import Portfolio
from apps.portfolios.services import transition_publication


def make_user(**kwargs) -> User:
    return cast(User, UserFactory(**kwargs))


def make_account(**kwargs) -> Account:
    return cast(Account, AccountFactory(**kwargs))


@pytest.mark.django_db
def test_refresh_rotation_reuse_revokes_family():
    user = make_user()
    session, raw = create_auth_session(user=user)
    other, _other_raw = create_auth_session(user=user)
    other.family_id = session.family_id
    other.save(update_fields=["family_id", "updated_at"])

    replacement, replacement_raw = rotate_refresh_token(raw)
    assert replacement.replaced_by_id is None
    assert replacement.family_id == session.family_id
    assert replacement.token_hash != raw
    with pytest.raises(RefreshTokenReplay):
        rotate_refresh_token(raw)

    session.refresh_from_db()
    other.refresh_from_db()
    replacement.refresh_from_db()
    assert session.revoked_at is not None
    assert other.revoked_at is not None
    assert replacement.revoked_at is not None
    assert replacement_raw


@pytest.mark.django_db
def test_revoked_session_access_token_is_rejected():
    user = make_user()
    token_data = issue_tokens(user)
    session = AuthSession.objects.get(pk=token_data["session_id"])
    revoke_session(session, actor=user)
    client = APIClient()
    response = client.get(
        "/api/me/",
        HTTP_AUTHORIZATION=f"Bearer {token_data['access']}",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_refresh_requires_csrf_header():
    user = make_user()
    token_data = issue_tokens(user)
    client = APIClient(enforce_csrf_checks=True)
    client.cookies["portfolio_refresh"] = token_data["refresh"]
    response = client.post("/api/auth/refresh/", HTTP_X_CORRELATION_ID="csrf-test")
    assert response.status_code == 403
    assert response["Content-Type"].startswith("application/json")
    assert response.json() == {
        "error": {
            "code": "csrf_failed",
            "message": "CSRF verification failed.",
            "fields": {},
            "correlation_id": "csrf-test",
        }
    }


@pytest.mark.django_db
def test_refresh_accepts_django_csrf_header():
    user = make_user()
    token_data = issue_tokens(user)
    client = APIClient(enforce_csrf_checks=True)
    csrf_response = client.get("/api/auth/csrf/")
    csrf_token = csrf_response.data["csrf_token"]
    client.cookies["portfolio_refresh"] = token_data["refresh"]
    response = client.post(
        "/api/auth/refresh/",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_totp_replay_and_recovery_code_single_use():
    user = make_user()
    uri = setup_totp(user)
    assert "otpauth://" in uri
    user.refresh_from_db()
    code = pyotp.TOTP(user.totp_pending_secret).now()
    recovery_codes = confirm_totp(user, code)
    user.refresh_from_db()
    assert user.totp_enabled
    assert not verify_totp_or_recovery(user, code)
    recovery = recovery_codes[0]
    assert verify_totp_or_recovery(user, recovery)
    assert not verify_totp_or_recovery(user, recovery)
    assert RecoveryCode.objects.filter(user=user, used_at__isnull=False).count() == 1


@pytest.mark.django_db
def test_staff_cannot_disable_totp():
    user = make_user(is_staff=True, totp_enabled=True, totp_secret=pyotp.random_base32())
    with pytest.raises(PermissionDenied):
        from apps.accounts.auth_services import disable_totp

        disable_totp(user, "000000")


@pytest.mark.django_db
def test_login_lockout_has_per_ip_and_account_backoff():
    cache.clear()
    user = make_user(email="locked@example.com")
    client = APIClient()
    for _ in range(5):
        response = client.post(
            "/api/auth/login/",
            {"email": user.email, "password": "wrong"},
            format="json",
        )
        assert response.status_code == 401
    response = client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "Password123!"},
        format="json",
    )
    assert response.status_code == 429
    assert get_state(key("account", user.email)).locked_until is not None
    assert get_state(key("ip", hash_ip("127.0.0.1"))).count >= 5


@pytest.mark.django_db
def test_login_failures_for_one_account_do_not_lock_out_another():
    cache.clear()
    first = make_user(email="first-login@example.com")
    second = make_user(email="second-login@example.com")
    client = APIClient()
    for _ in range(5):
        response = client.post(
            "/api/auth/login/",
            {"email": first.email, "password": "wrong"},
            format="json",
        )
        assert response.status_code == 401
    response = client.post(
        "/api/auth/login/",
        {"email": second.email, "password": "Password123!"},
        format="json",
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_ip_spray_control_triggers_across_accounts():
    cache.clear()
    client = APIClient()
    for index in range(20):
        user = make_user(email=f"spray-{index}@example.com")
        response = client.post(
            "/api/auth/login/",
            {"email": user.email, "password": "wrong"},
            format="json",
        )
        assert response.status_code == 401
    victim = make_user(email="spray-victim@example.com")
    response = client.post(
        "/api/auth/login/",
        {"email": victim.email, "password": "Password123!"},
        format="json",
    )
    assert response.status_code == 429


@pytest.mark.django_db
def test_request_ip_requires_trusted_proxy_for_forwarded_headers():
    request = APIRequestFactory().get(
        "/",
        REMOTE_ADDR="10.0.0.2",
        HTTP_X_FORWARDED_FOR="198.51.100.1, 203.0.113.4",
    )
    assert request_ip(request) == "10.0.0.2"
    with override_settings(AUTH_TRUSTED_PROXIES=["10.0.0.2"]):
        assert request_ip(request) == "203.0.113.4"


@pytest.mark.django_db
def test_login_2fa_returns_challenge_before_tokens():
    cache.clear()
    user = make_user(totp_enabled=True, totp_secret=pyotp.random_base32())
    client = APIClient()
    response = client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "Password123!"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["requires_2fa"]
    assert "access" not in response.data
    challenge = response.data["challenge_id"]
    code = pyotp.TOTP(user.totp_secret).now()
    completed = client.post(
        "/api/auth/login/2fa/",
        {"challenge_id": challenge, "code": code},
        format="json",
    )
    assert completed.status_code == 200
    assert completed.data["access"]
    assert client.cookies["portfolio_refresh"]["httponly"]
    assert bool(client.cookies["portfolio_refresh"]["secure"]) == settings.SESSION_COOKIE_SECURE
    assert client.cookies["portfolio_refresh"]["samesite"] == "Strict"
    assert client.cookies["portfolio_refresh"]["path"] == "/api/auth/refresh/"


@pytest.mark.django_db
def test_explicit_unverified_actor_cannot_publish_verified_actor_can():
    user = make_user(is_email_verified=False)
    account = make_account()
    MembershipFactory(account=account, user=user)
    portfolio = Portfolio.all_objects.create(
        account=account,
        title="Publish",
        slug="publish-auth",
    )
    with pytest.raises(PermissionDenied):
        transition_publication(
            portfolio=portfolio,
            target=Portfolio.STATE_PUBLISHED,
            actor=user,
        )
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified", "updated_at"])
    transition_publication(
        portfolio=portfolio,
        target=Portfolio.STATE_PUBLISHED,
        actor=user,
    )
    portfolio.refresh_from_db()
    assert portfolio.publication_state == Portfolio.STATE_PUBLISHED


@pytest.mark.django_db
def test_publication_requires_an_explicit_actor():
    account = make_account()
    portfolio = Portfolio.all_objects.create(
        account=account,
        title="Publish",
        slug="publish-missing-actor",
    )
    with pytest.raises(PermissionDenied):
        transition_publication(
            portfolio=portfolio,
            target=Portfolio.STATE_PUBLISHED,
        )


@pytest.mark.django_db
def test_verification_and_password_reset_tokens_are_single_use():
    user = make_user()
    verification = issue_verification_token(user)
    confirmed = confirm_verification(verification)
    assert confirmed.is_email_verified
    with pytest.raises(ValidationError):
        confirm_verification(verification)

    session_data = issue_tokens(user)
    reset = issue_password_reset_token(user)
    reset_password(raw=reset, password="NewPassword123!")
    session = AuthSession.objects.get(pk=session_data["session_id"])
    assert session.revoked_at is not None
    with pytest.raises(ValidationError):
        reset_password(raw=reset, password="AnotherPassword123!")


@pytest.mark.django_db
def test_access_authentication_rejects_bad_headers_and_tokens():
    factory = APIRequestFactory()
    authenticator = AccessTokenAuthentication()
    assert authenticator.authenticate(Request(factory.get("/"))) is None
    with pytest.raises(AuthenticationFailed):
        authenticator.authenticate(Request(factory.get("/", HTTP_AUTHORIZATION="Basic abc")))
    with pytest.raises(AuthenticationFailed):
        authenticator.authenticate(Request(factory.get("/", HTTP_AUTHORIZATION="Bearer bad")))
    with pytest.raises(InvalidAccessToken):
        decode_access_token("not-a-jwt")
    wrong_type = jwt.encode(
        {
            "sub": "user",
            "sid": "session",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "iss": settings.AUTH_JWT_ISSUER,
            "type": "refresh",
        },
        settings.AUTH_JWT_SIGNING_KEY,
        algorithm="HS256",
    )
    with pytest.raises(InvalidAccessToken):
        decode_access_token(wrong_type)


@pytest.mark.django_db
def test_access_authentication_cache_and_session_failure_paths():
    user = make_user()
    token_data = issue_tokens(user)
    request = Request(
        APIRequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {token_data['access']}")
    )
    authenticator = AccessTokenAuthentication()
    with patch("apps.accounts.authentication.cache.get", return_value=True):
        with pytest.raises(AuthenticationFailed):
            authenticator.authenticate(request)
    with patch("apps.accounts.authentication.cache.get", return_value=False):
        authenticated = authenticator.authenticate(request)
        assert authenticated is not None
        assert authenticated[0] == user
        AuthSession.objects.filter(pk=token_data["session_id"]).delete()
        with pytest.raises(AuthenticationFailed):
            authenticator.authenticate(request)
    with patch("apps.accounts.authentication.cache.set", side_effect=RuntimeError("redis down")):
        mark_session_revoked(str(user.pk))


@pytest.mark.django_db
def test_access_authentication_rejects_db_revocation_when_cache_is_down():
    user = make_user()
    token_data = issue_tokens(user)
    session = AuthSession.objects.get(pk=token_data["session_id"])
    session.revoked_at = session.created_at
    session.save(update_fields=["revoked_at", "updated_at"])
    request = Request(
        APIRequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {token_data['access']}")
    )
    with patch("apps.accounts.authentication.cache.get", side_effect=RuntimeError("redis down")):
        with pytest.raises(AuthenticationFailed):
            AccessTokenAuthentication().authenticate(request)


@pytest.mark.django_db
def test_access_authentication_rejects_database_revocation_and_inactive_user():
    user = make_user()
    token_data = issue_tokens(user)
    session = AuthSession.objects.get(pk=token_data["session_id"])
    session.revoked_at = session.created_at
    session.save(update_fields=["revoked_at", "updated_at"])
    request = Request(
        APIRequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {token_data['access']}")
    )
    with patch("apps.accounts.authentication.cache.get", return_value=False):
        with pytest.raises(AuthenticationFailed):
            AccessTokenAuthentication().authenticate(request)

    inactive = make_user(is_active=False)
    inactive_tokens = issue_tokens(inactive)
    inactive_request = Request(
        APIRequestFactory().get(
            "/",
            HTTP_AUTHORIZATION=f"Bearer {inactive_tokens['access']}",
        )
    )
    with patch("apps.accounts.authentication.cache.get", return_value=False):
        with pytest.raises(AuthenticationFailed):
            AccessTokenAuthentication().authenticate(inactive_request)


@pytest.mark.django_db
def test_two_factor_challenge_exhaustion_invalidates_challenge():
    cache.clear()
    user = make_user(totp_enabled=True, totp_secret=pyotp.random_base32())
    client = APIClient()
    login = client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "Password123!"},
        format="json",
    )
    challenge = login.data["challenge_id"]
    for _ in range(5):
        response = client.post(
            "/api/auth/login/2fa/",
            {"challenge_id": challenge, "code": "000000"},
            format="json",
        )
        assert response.status_code == 401
    assert cache.get(f"auth:challenge:{challenge}") is None


@pytest.mark.django_db
def test_inactive_user_is_rejected_from_login():
    cache.clear()
    user = make_user(is_active=False)
    response = APIClient().post(
        "/api/auth/login/",
        {"email": user.email, "password": "Password123!"},
        format="json",
    )
    assert response.status_code == 401
    assert not AuthSession.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_successful_login_only_clears_account_throttle_counter():
    cache.clear()
    user = make_user()
    client = APIClient()
    failed = client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "wrong"},
        format="json",
    )
    assert failed.status_code == 401
    response = client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "Password123!"},
        format="json",
    )
    assert response.status_code == 200
    assert get_state(key("account", user.email)).count == 0
    assert get_state(key("ip", hash_ip("127.0.0.1"))).count >= 1


@pytest.mark.django_db
def test_signup_is_throttled_per_ip():
    cache.clear()
    client = APIClient()
    for index in range(24):
        response = client.post(
            "/api/auth/signup/",
            {
                "email": f"signup-{index}@example.com",
                "password": "Password123!",
                "account_name": f"Signup {index}",
                "account_slug": f"signup-{index}",
                "portfolio_title": "Portfolio",
                "portfolio_slug": f"portfolio-{index}",
            },
            format="json",
        )
        assert response.status_code == 201
    response = client.post(
        "/api/auth/signup/",
        {
            "email": "signup-locked@example.com",
            "password": "Password123!",
            "account_name": "Locked",
            "account_slug": "signup-locked",
            "portfolio_title": "Portfolio",
            "portfolio_slug": "portfolio-locked",
        },
        format="json",
    )
    assert response.status_code == 429


@pytest.mark.django_db
def test_verification_requests_queue_distinct_messages_for_distinct_tokens():
    cache.clear()
    user = make_user(is_email_verified=False)
    client = APIClient()
    payload = {"email": user.email}
    assert client.post("/api/auth/verification/request/", payload, format="json").status_code == 200
    assert client.post("/api/auth/verification/request/", payload, format="json").status_code == 200
    messages = EmailMessage.objects.filter(template_code="email_verification")
    assert messages.count() == 2
    assert messages.values_list("related_object_ref", flat=True).distinct().count() == 2


@pytest.mark.django_db
def test_access_tokens_use_configured_issuer_and_signing_key():
    user = make_user()
    with override_settings(
        AUTH_JWT_ISSUER="test-issuer",
        AUTH_JWT_SIGNING_KEY="test-signing-key-that-is-at-least-32-bytes",
    ):
        token_data = issue_tokens(user)
        claims = decode_access_token(token_data["access"])
    assert claims["iss"] == "test-issuer"
