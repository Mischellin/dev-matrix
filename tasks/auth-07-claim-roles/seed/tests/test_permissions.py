from gateway import derive_permissions, is_allowed


def test_editor_with_matching_scope() -> None:
    claims = {"scope": "read write", "roles": ["editor"]}
    assert derive_permissions(claims, "alpha") == ["docs:read", "docs:write"]


def test_empty_claims_yield_nothing() -> None:
    assert derive_permissions({}, "alpha") == []
    assert not is_allowed({}, "alpha", "docs:read")


def test_result_is_sorted() -> None:
    claims = {"scope": "admin", "roles": ["admin"]}
    result = derive_permissions(claims, "alpha")
    assert result == sorted(result)
    assert is_allowed(claims, "alpha", "docs:delete")
