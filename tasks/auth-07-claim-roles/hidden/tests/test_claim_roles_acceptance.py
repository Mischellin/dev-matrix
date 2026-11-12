import copy

from gateway import ROLE_PERMISSIONS, derive_permissions, is_allowed


def test_broad_scope_without_roles_grants_nothing() -> None:
    claims = {"scope": "read write admin openid"}
    assert derive_permissions(claims, "alpha") == []
    assert not is_allowed(claims, "alpha", "docs:delete")


def test_narrow_scope_does_not_remove_role_permissions() -> None:
    claims = {"scope": "openid", "roles": ["admin"]}
    assert derive_permissions(claims, "alpha") == [
        "docs:delete",
        "docs:read",
        "docs:write",
        "members:manage",
    ]


def test_scope_does_not_extend_roles() -> None:
    claims = {"scope": "admin", "roles": ["viewer"]}
    assert derive_permissions(claims, "alpha") == ["docs:read"]


def test_project_roles_apply_per_project() -> None:
    claims = {"project_roles": {"alpha": ["editor"], "beta": ["viewer"]}}
    assert derive_permissions(claims, "alpha") == ["docs:read", "docs:write"]
    assert derive_permissions(claims, "beta") == ["docs:read"]


def test_flat_roles_are_fallback_for_unlisted_project() -> None:
    claims = {"project_roles": {"alpha": ["admin"]}, "roles": ["viewer"]}
    assert derive_permissions(claims, "gamma") == ["docs:read"]
    assert derive_permissions({"roles": ["billing"]}, "any") == ["billing:manage", "billing:read"]


def test_project_entry_overrides_flat_roles_even_when_empty() -> None:
    claims = {"project_roles": {"alpha": []}, "roles": ["admin"]}
    assert derive_permissions(claims, "alpha") == []
    claims = {"project_roles": {"alpha": ["viewer"]}, "roles": ["admin"]}
    assert derive_permissions(claims, "alpha") == ["docs:read"]


def test_unknown_roles_and_non_string_items_are_ignored() -> None:
    claims = {"roles": ["superuser", "Admin", 7, None, ["admin"], {"a": 1}, "viewer"]}
    assert derive_permissions(claims, "alpha") == ["docs:read"]


def test_malformed_claim_shapes_do_not_raise() -> None:
    assert derive_permissions({"roles": "admin"}, "alpha") == []
    assert derive_permissions({"roles": {"admin": True}}, "alpha") == []
    assert derive_permissions({"project_roles": ["alpha"]}, "alpha") == []
    assert derive_permissions({"project_roles": "alpha", "roles": ["viewer"]}, "alpha") == [
        "docs:read"
    ]
    assert derive_permissions(
        {"project_roles": {"alpha": "admin"}, "roles": ["viewer"]}, "alpha"
    ) == ["docs:read"]


def test_union_is_deduplicated_and_sorted() -> None:
    claims = {"roles": ["editor", "viewer", "editor", "billing", "admin"]}
    result = derive_permissions(claims, "alpha")
    assert result == sorted(set(result))
    assert result == [
        "billing:manage",
        "billing:read",
        "docs:delete",
        "docs:read",
        "docs:write",
        "members:manage",
    ]


def test_is_allowed_follows_roles() -> None:
    claims = {"scope": "admin", "project_roles": {"alpha": ["editor"]}}
    assert is_allowed(claims, "alpha", "docs:write")
    assert not is_allowed(claims, "alpha", "docs:delete")
    assert not is_allowed(claims, "beta", "docs:read")


def test_claims_are_not_mutated_and_table_is_complete() -> None:
    claims = {
        "scope": "read",
        "roles": ["viewer", 1],
        "project_roles": {"alpha": ["editor", "admin"]},
    }
    snapshot = copy.deepcopy(claims)
    derive_permissions(claims, "alpha")
    assert claims == snapshot
    assert set(ROLE_PERMISSIONS) == {"viewer", "editor", "admin", "billing"}
