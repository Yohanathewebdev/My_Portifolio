from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import User


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    account_name = serializers.CharField(max_length=200)
    account_slug = serializers.SlugField(max_length=80)
    portfolio_title = serializers.CharField(max_length=200)
    portfolio_slug = serializers.SlugField(max_length=80)
    billing_email = serializers.EmailField(required=False, allow_blank=True)
    country_code = serializers.CharField(max_length=2, required=False, allow_blank=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class LoginChallengeSerializer(serializers.Serializer):
    challenge_id = serializers.CharField()
    code = serializers.CharField(max_length=64)


class TokenSerializer(serializers.Serializer):
    access = serializers.CharField()
    session_id = serializers.UUIDField()


class VerificationSerializer(serializers.Serializer):
    token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)


class TotpCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=64)


class SessionSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="pk")
    family_id = serializers.UUIDField()
    user_agent = serializers.CharField()
    created_at = serializers.DateTimeField()
    last_used_at = serializers.DateTimeField()
    revoked_at = serializers.DateTimeField()


class UserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "is_email_verified", "totp_enabled"]
        read_only_fields = fields
