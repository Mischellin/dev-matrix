"""Permission derivation for verified access-token claims."""

from collections.abc import Mapping
from typing import Any

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"docs:read"}),
    "editor": frozenset({"docs:read", "docs:write"}),
    "admin": frozenset({"docs:read", "docs:write", "docs:delete", "members:manage"}),
    "billing": frozenset({"billing:read", "billing:manage"}),
}


def _select_roles(claims: Mapping[str, Any], project: str) -> list[Any]:
    """Pick the role list for ``project``: project entry first, flat ``roles`` as fallback."""
    project_roles = claims.get("project_roles")
    if isinstance(project_roles, Mapping):
        entry = project_roles.get(project)
        if isinstance(entry, list):
            return entry
    flat = claims.get("roles")
    return flat if isinstance(flat, list) else []


def derive_permissions(claims: Mapping[str, Any], project: str) -> list[str]:
    """Return the sorted permissions the token holder has in ``project``."""
    result: set[str] = set()
    for role in _select_roles(claims, project):
        if isinstance(role, str):
            result |= ROLE_PERMISSIONS.get(role, frozenset())
    return sorted(result)


def is_allowed(claims: Mapping[str, Any], project: str, permission: str) -> bool:
    """Check whether the token holder has ``permission`` in ``project``."""
    return permission in derive_permissions(claims, project)
