from __future__ import annotations

from typing import cast

from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Account, AccountMembership, User
from apps.accounts.services import (
    change_member_role,
    invite_member,
    remove_member,
    transfer_ownership,
)
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


class CurrentUserViewSet(AccountScopedViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.none()

    def list(self, request):
        return Response(UserSerializer(request.user).data)


class AccountViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    AccountScopedViewSet,
):
    serializer_class = AccountSerializer
    queryset = Account.all_objects.none()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.kwargs.get("pk"):
            queryset = queryset.filter(pk=self.kwargs["pk"])
        return queryset


class MembershipViewSet(
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
            actor=request.user,
        )
        return Response(MembershipSerializer(membership).data)

    def destroy(self, request, *args, **kwargs):
        remove_member(membership=self.get_object(), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def transfer_ownership(self, request, *args, **kwargs):
        if self.get_request_role() != AccountMembership.ROLE_OWNER:
            raise PermissionDenied
        replacement = self.get_queryset().filter(pk=request.data.get("new_owner_id")).first()
        if replacement is None:
            raise PermissionDenied
        _, replacement = transfer_ownership(
            membership=self.get_object(),
            new_owner=replacement,
            actor=request.user,
        )
        return Response(MembershipSerializer(replacement).data)


class PortfolioViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    AccountScopedViewSet,
):
    serializer_class = PortfolioSerializer
    queryset = Portfolio.all_objects.none()

    def get_permissions(self):
        if self.kwargs.get("account_id"):
            self.get_request_account()
        permission_class: type[BasePermission]
        if self.action in {"list", "retrieve"}:
            permission_class = ReadDraftPermission
        elif self.action == "destroy":
            permission_class = DeletePortfolioPermission
        else:
            permission_class = CreateEditPermission
        return [permission_class()]

    def get_queryset(self):
        if self.kwargs.get("account_id"):
            queryset = super().get_queryset().filter(account_id=self.kwargs["account_id"])
        elif self.kwargs.get("pk"):
            portfolio = cast(Portfolio, default_portfolio_resolver(self.request))
            queryset = super().get_queryset().filter(pk=portfolio.pk)
        else:
            queryset = super().get_queryset()
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
        from apps.portfolios.services import update_portfolio

        portfolio = update_portfolio(
            portfolio=portfolio,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(PortfolioSerializer(portfolio).data)

    partial_update = update

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
