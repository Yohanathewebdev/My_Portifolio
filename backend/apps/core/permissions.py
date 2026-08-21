from __future__ import annotations

from dataclasses import dataclass

from rest_framework.permissions import BasePermission

ROLES = ("owner", "admin", "editor", "viewer", "platform_support", "anonymous")


@dataclass(frozen=True)
class PermissionCell:
    allowed: bool
    implemented: bool = True
    deferred_to: str | None = None


ROLE_MATRIX: dict[str, dict[str, PermissionCell]] = {
    "read_published": {
        "owner": PermissionCell(True),
        "admin": PermissionCell(True),
        "editor": PermissionCell(True),
        "viewer": PermissionCell(True),
        "platform_support": PermissionCell(True),
        "anonymous": PermissionCell(True),
    },
    "read_draft": {
        "owner": PermissionCell(True),
        "admin": PermissionCell(True),
        "editor": PermissionCell(True),
        "viewer": PermissionCell(True),
        "platform_support": PermissionCell(False, False, "Phase 5"),
        "anonymous": PermissionCell(False, False, "Phase 1b preview tokens"),
    },
    "create_edit_content": {
        "owner": PermissionCell(True),
        "admin": PermissionCell(True),
        "editor": PermissionCell(True),
        "viewer": PermissionCell(False),
        "platform_support": PermissionCell(False),
        "anonymous": PermissionCell(False),
    },
    "publish_unpublish": {
        "owner": PermissionCell(True),
        "admin": PermissionCell(True),
        "editor": PermissionCell(False),
        "viewer": PermissionCell(False),
        "platform_support": PermissionCell(False),
        "anonymous": PermissionCell(False),
    },
    "manage_theme": {
        "owner": PermissionCell(True),
        "admin": PermissionCell(True),
        "editor": PermissionCell(False),
        "viewer": PermissionCell(False),
        "platform_support": PermissionCell(False),
        "anonymous": PermissionCell(False),
    },
    "read_leads": {
        "owner": PermissionCell(True),
        "admin": PermissionCell(True),
        "editor": PermissionCell(True),
        "viewer": PermissionCell(False),
        "platform_support": PermissionCell(False),
        "anonymous": PermissionCell(False),
    },
    "manage_members": {
        "owner": PermissionCell(True),
        "admin": PermissionCell(True),
        "editor": PermissionCell(False),
        "viewer": PermissionCell(False),
        "platform_support": PermissionCell(False),
        "anonymous": PermissionCell(False),
    },
    "manage_billing": {
        "owner": PermissionCell(True),
        "admin": PermissionCell(False),
        "editor": PermissionCell(False),
        "viewer": PermissionCell(False),
        "platform_support": PermissionCell(False),
        "anonymous": PermissionCell(False),
    },
    "delete_portfolio": {
        "owner": PermissionCell(True),
        "admin": PermissionCell(False),
        "editor": PermissionCell(False),
        "viewer": PermissionCell(False),
        "platform_support": PermissionCell(False),
        "anonymous": PermissionCell(False),
    },
    "suspend_portfolio": {
        "owner": PermissionCell(False),
        "admin": PermissionCell(False),
        "editor": PermissionCell(False),
        "viewer": PermissionCell(False),
        "platform_support": PermissionCell(True),
        "anonymous": PermissionCell(False),
    },
    "impersonate_user": {
        "owner": PermissionCell(False),
        "admin": PermissionCell(False),
        "editor": PermissionCell(False),
        "viewer": PermissionCell(False),
        "platform_support": PermissionCell(True),
        "anonymous": PermissionCell(False),
    },
}


def matrix_cell(action: str, role: str) -> PermissionCell:
    return ROLE_MATRIX[action][role]


class RolePermission(BasePermission):
    action_name = ""

    def has_permission(self, request, view) -> bool:
        role = getattr(view, "get_request_role", lambda: "anonymous")()
        cell = matrix_cell(self.action_name or getattr(view, "permission_action", ""), role)
        return cell.implemented and cell.allowed


class ManageMembersPermission(RolePermission):
    action_name = "manage_members"


class ManageBillingPermission(RolePermission):
    action_name = "manage_billing"


class CreateEditPermission(RolePermission):
    action_name = "create_edit_content"


class ReadDraftPermission(RolePermission):
    action_name = "read_draft"


class DeletePortfolioPermission(RolePermission):
    action_name = "delete_portfolio"
