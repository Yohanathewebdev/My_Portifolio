from types import SimpleNamespace

import pytest

from apps.core.permissions import ROLE_MATRIX, ROLES, RolePermission, matrix_cell


def test_role_matrix_contains_every_declared_cell():
    assert ROLE_MATRIX
    for action, cells in ROLE_MATRIX.items():
        assert set(cells) == set(ROLES), action
        for role in ROLES:
            cell = matrix_cell(action, role)
            assert cell.implemented or cell.deferred_to


def test_role_permission_denies_deferred_and_anonymous_cells():
    permission = RolePermission()
    permission.action_name = "read_draft"
    view = SimpleNamespace(get_request_role=lambda: "platform_support")
    assert not permission.has_permission(None, view)
    view = SimpleNamespace(get_request_role=lambda: "owner")
    assert permission.has_permission(None, view)


@pytest.mark.parametrize(
    ("action", "role"),
    [(action, role) for action in ROLE_MATRIX for role in ROLES],
)
def test_every_matrix_cell_is_evaluated(action, role):
    permission = RolePermission()
    permission.action_name = action
    view = SimpleNamespace(get_request_role=lambda: role)
    cell = matrix_cell(action, role)
    assert permission.has_permission(None, view) is (cell.allowed and cell.implemented)
