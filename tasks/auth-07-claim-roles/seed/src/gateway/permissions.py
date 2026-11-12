"""Permission derivation for verified access-token claims."""

from collections.abc import Mapping
from typing import Any

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"docs:read"}),
    "editor": frozenset({"docs:read", "docs:write"}),
    "admin": frozenset({"docs:read", "docs:write", "docs:delete", "members:manage"}),
    "billing": frozenset({"billing:read", "billing:manage"}),
}

# Legacy mapping of OAuth scope tokens to permissions.
SCOPE_PERMISSIONS: dict[str, frozenset[str]] = {
    "read": frozenset({"docs:read"}),
    "write": frozenset({"docs:read", "docs:write"}),
    "admin": frozenset(
        {
            "docs:read",
            "docs:write",
            "docs:delete",
            "members:manage",
            "billing:read",
            "billing:manage",
        }
    ),
}


def derive_permissions(claims: Mapping[str, Any], project: str) -> list[str]:
    """Return the sorted permissions the token holder has in ``project``."""
    scope = claims.get("scope", "")
    tokens = scope.split() if isinstance(scope, str) else []
    result: set[str] = set()
    for token in tokens:
        result |= SCOPE_PERMISSIONS.get(token, frozenset())
    return sorted(result)


def is_allowed(claims: Mapping[str, Any], project: str, permission: str) -> bool:
    """Check whether the token holder has ``permission`` in ``project``."""
    return permission in derive_permissions(claims, project)
