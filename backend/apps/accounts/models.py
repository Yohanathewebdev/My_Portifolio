from __future__ import annotations

from typing import ClassVar

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.core.managers import AccountScopedManager
from apps.core.models import BaseModel
from apps.core.slug_registry import validate_reserved_slug


class UserManager(BaseUserManager["User"]):
    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("email is required")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)


class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects: ClassVar[UserManager] = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    def __str__(self) -> str:
        return self.email


class Account(BaseModel):
    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_SUSPENDED, "Suspended"),
        (STATUS_CLOSED, "Closed"),
    )

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    plan_ref = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    billing_email = models.EmailField()
    country_code = models.CharField(max_length=2, blank=True)
    entitlement_overrides = models.JSONField(default=dict, blank=True)

    objects: ClassVar[AccountScopedManager] = AccountScopedManager()
    all_objects: ClassVar[models.Manager] = models.Manager()  # type: ignore[no-redef]

    class Meta:
        base_manager_name = "all_objects"
        default_manager_name = "objects"

    def save(self, *args, **kwargs):
        validate_reserved_slug(self.slug)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class AccountMembership(BaseModel):
    ROLE_OWNER = "owner"
    ROLE_ADMIN = "admin"
    ROLE_EDITOR = "editor"
    ROLE_VIEWER = "viewer"
    ROLE_CHOICES = (
        (ROLE_OWNER, "Owner"),
        (ROLE_ADMIN, "Admin"),
        (ROLE_EDITOR, "Editor"),
        (ROLE_VIEWER, "Viewer"),
    )

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    invited_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_membership_invites",
    )
    invited_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    objects: ClassVar[AccountScopedManager] = AccountScopedManager()
    all_objects: ClassVar[models.Manager] = models.Manager()  # type: ignore[no-redef]

    class Meta:
        base_manager_name = "all_objects"
        default_manager_name = "objects"
        constraints = [
            models.UniqueConstraint(fields=["account", "user"], name="unique_account_user"),
            models.UniqueConstraint(
                fields=["account"],
                condition=models.Q(role="owner"),
                name="one_account_owner",
            ),
        ]
