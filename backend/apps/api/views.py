from __future__ import annotations

from typing import Protocol, cast
from uuid import UUID

from django.http import Http404
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import Account, AccountMembership, User
from apps.accounts.services import change_member_role, invite_member, remove_member
from apps.api.serializers import (
    AccountSerializer,
    MembershipInviteSerializer,
    MembershipSerializer,
    PortfolioSerializer,
    UserSerializer,
)
from apps.core.permissions import (
    CreateEditPermission,
    DeletePortfolioPermission,
    ManageMembersPermission,
    ReadDraftPermission,
)
from apps.core.views import AccountScopedViewSet, default_portfolio_resolver
from apps.portfolios.models import Portfolio
from apps.portfolios.services import create_portfolio


class AccountRoleMixin:
    def get_request_account(self):
        view = cast(AccountRoleView, self)
        account_id = view.kwargs.get("account_id")
        try:
            account = Account.all_objects.get(pk=cast(UUID | str, account_id))
        except Account.DoesNotExist:
            raise Http404 from None
        if not AccountMembership.all_objects.filter(
            account=account,
            user=cast(User, view.request.user),
            accepted_at__isnull=False,
        ).exists():
            raise Http404
        return account

    def get_request_role(self):
        view = cast(AccountRoleView, self)
        membership = AccountMembership.all_objects.filter(
            account=self.get_request_account(),
            user=cast(User, view.request.user),
            accepted_at__isnull=False,
        ).first()
        return membership.role if membership else "anonymous"


class AccountRoleView(Protocol):
    kwargs: dict[str, object]
    request: Request


class CurrentUserViewSet(AccountScopedViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.none()

    def list(self, request):
        return Response(UserSerializer(request.user).data)


class AccountViewSet(
    AccountRoleMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    AccountScopedViewSet,
):
    serializer_class = AccountSerializer
    permission_classes = []
    queryset = Account.all_objects.none()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.kwargs.get("pk"):
            queryset = queryset.filter(pk=self.kwargs["pk"])
        return queryset


class MembershipViewSet(
    AccountRoleMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    AccountScopedViewSet,
):
    serializer_class = MembershipSerializer
    permission_classes = [ManageMembersPermission]
    queryset = AccountMembership.all_objects.none()

    def get_queryset(self):
        queryset = super().get_queryset().filter(account_id=self.kwargs["account_id"])
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = MembershipInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = invite_member(
            account=self.get_request_account(),
            inviter=request.user,
            **serializer.validated_data,
        )
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"])
    def role(self, request, *args, **kwargs):
        membership = self.get_object()
        serializer = MembershipInviteSerializer(
            data={"email": membership.user.email, "role": request.data.get("role")}
        )
        serializer.is_valid(raise_exception=True)
        membership = change_member_role(
            membership=membership,
            role=serializer.validated_data["role"],
        )
        return Response(MembershipSerializer(membership).data)

    def destroy(self, request, *args, **kwargs):
        remove_member(membership=self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


class PortfolioViewSet(
    AccountRoleMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    AccountScopedViewSet,
):
    serializer_class = PortfolioSerializer
    queryset = Portfolio.all_objects.none()

    def get_permissions(self):
        permission_class: type[BasePermission]
        if self.action in {"list", "retrieve"}:
            permission_class = ReadDraftPermission
        elif self.action == "destroy":
            permission_class = DeletePortfolioPermission
        else:
            permission_class = CreateEditPermission
        return [permission_class()]

    def get_queryset(self):
        queryset = super().get_queryset().filter(account_id=self.kwargs["account_id"])
        if self.kwargs.get("pk"):
            queryset = queryset.filter(pk=self.kwargs["pk"])
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = PortfolioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        portfolio = create_portfolio(
            account=self.get_request_account(),
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(PortfolioSerializer(portfolio).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        portfolio = self.get_object()
        serializer = PortfolioSerializer(portfolio, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(portfolio, field, value)
        portfolio.save()
        return Response(PortfolioSerializer(portfolio).data)

    partial_update = update

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PortfolioDetailViewSet(AccountScopedViewSet):
    serializer_class = PortfolioSerializer
    queryset = Portfolio.all_objects.none()

    def get_portfolio(self):
        return default_portfolio_resolver(self.request)

    def get_accounts(self):
        return [self.get_portfolio().account_id]

    def get_queryset(self):
        return super().get_queryset().filter(pk=self.get_portfolio().pk)

    def retrieve(self, request, *args, **kwargs):
        return Response(PortfolioSerializer(self.get_object()).data)
