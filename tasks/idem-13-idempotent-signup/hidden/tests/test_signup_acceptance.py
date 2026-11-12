import pytest
from signup import ConflictError, InMemoryStore, StoreError, signup

EMAIL = "owner@example.com"
TAX = "TX100200"


def counts(store):
    return len(store.accounts), len(store.memberships), len(store.subscriptions)


def test_repeat_call_returns_same_account_without_duplicates():
    store = InMemoryStore()
    first = signup(store, EMAIL, TAX, "Acme Ltd")
    second = signup(store, EMAIL, TAX, "Acme Ltd")
    assert first.created is True
    assert second.created is False
    assert second.account.id == first.account.id
    assert counts(store) == (1, 1, 1)


def test_email_is_normalised():
    store = InMemoryStore()
    first = signup(store, EMAIL, TAX, "Acme Ltd")
    second = signup(store, "  Owner@Example.COM ", TAX, "Acme Ltd")
    assert second.created is False
    assert second.account.id == first.account.id
    assert store.accounts[0].owner_email == EMAIL
    assert store.memberships[0].email == EMAIL
    assert counts(store) == (1, 1, 1)


def test_tax_id_is_normalised():
    store = InMemoryStore()
    first = signup(store, EMAIL, "tx-100 200", "Acme Ltd")
    second = signup(store, EMAIL, " TX100200 ", "Acme Ltd")
    assert second.created is False
    assert second.account.id == first.account.id
    assert store.accounts[0].tax_id == TAX
    assert counts(store) == (1, 1, 1)


def test_same_email_different_tax_id_is_a_different_account():
    store = InMemoryStore()
    first = signup(store, EMAIL, TAX, "Acme Ltd")
    second = signup(store, EMAIL, "TX999", "Acme Ltd")
    assert second.created is True
    assert second.account.id != first.account.id
    assert counts(store) == (2, 2, 2)


@pytest.mark.parametrize("step", ["membership", "subscription"])
def test_retry_after_failure_completes_missing_steps_once(step):
    store = InMemoryStore()
    store.fail_on(step)
    with pytest.raises(StoreError):
        signup(store, EMAIL, TAX, "Acme Ltd", plan="pro")
    result = signup(store, EMAIL, TAX, "Acme Ltd", plan="pro")
    assert result.created is True
    assert counts(store) == (1, 1, 1)
    assert store.accounts[0].id == result.account.id
    assert store.subscriptions[0].plan == "pro"
    again = signup(store, EMAIL, TAX, "Acme Ltd", plan="pro")
    assert again.created is False
    assert counts(store) == (1, 1, 1)


def test_retry_after_failure_at_account_step():
    store = InMemoryStore()
    store.fail_on("account")
    with pytest.raises(StoreError):
        signup(store, EMAIL, TAX, "Acme Ltd")
    assert counts(store) == (0, 0, 0)
    result = signup(store, EMAIL, TAX, "Acme Ltd")
    assert result.created is True
    assert counts(store) == (1, 1, 1)


def test_repeated_failures_never_leave_duplicates():
    store = InMemoryStore()
    store.fail_on("membership", times=2)
    for _ in range(2):
        with pytest.raises(StoreError):
            signup(store, EMAIL, TAX, "Acme Ltd")
    result = signup(store, EMAIL, TAX, "Acme Ltd")
    assert result.created is True
    assert counts(store) == (1, 1, 1)


def test_conflicting_business_name_raises():
    store = InMemoryStore()
    signup(store, EMAIL, TAX, "Acme Ltd")
    with pytest.raises(ConflictError):
        signup(store, EMAIL, TAX, "Other Corp")
    assert counts(store) == (1, 1, 1)
    assert store.accounts[0].business_name == "Acme Ltd"


def test_conflict_is_detected_on_partially_created_account():
    store = InMemoryStore()
    store.fail_on("subscription")
    with pytest.raises(StoreError):
        signup(store, EMAIL, TAX, "Acme Ltd")
    with pytest.raises(ConflictError):
        signup(store, EMAIL, TAX, "Other Corp")
    assert counts(store) == (1, 1, 0)


def test_business_name_differing_in_case_and_spaces_is_not_a_conflict():
    store = InMemoryStore()
    first = signup(store, EMAIL, TAX, "Acme Ltd")
    second = signup(store, EMAIL, TAX, "  ACME   ltd ")
    assert second.created is False
    assert second.account.id == first.account.id
    assert counts(store) == (1, 1, 1)


def test_repeat_with_other_plan_keeps_original_subscription():
    store = InMemoryStore()
    signup(store, EMAIL, TAX, "Acme Ltd", plan="pro")
    result = signup(store, EMAIL, TAX, "Acme Ltd", plan="enterprise")
    assert result.created is False
    assert [s.plan for s in store.subscriptions] == ["pro"]


def test_interleaved_request_does_not_create_duplicates():
    store = InMemoryStore()
    inner = {}

    def other_request():
        inner["result"] = signup(store, EMAIL, TAX, "Acme Ltd")

    store.before("membership", other_request)
    outer = signup(store, EMAIL, TAX, "Acme Ltd")
    assert outer.account.id == inner["result"].account.id
    assert counts(store) == (1, 1, 1)


def test_invalid_input_is_rejected_before_any_write():
    store = InMemoryStore()
    for email, tax in [("", TAX), ("no-at-sign", TAX), (EMAIL, "  "), (EMAIL, " - ")]:
        with pytest.raises(ValueError):
            signup(store, email, tax, "Acme Ltd")
    assert counts(store) == (0, 0, 0)
