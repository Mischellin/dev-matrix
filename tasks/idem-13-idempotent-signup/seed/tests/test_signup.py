import pytest
from signup import InMemoryStore, StoreError, signup


def test_first_signup_creates_everything():
    store = InMemoryStore()
    result = signup(store, "owner@example.com", "TX100", "Acme Ltd", plan="pro")
    assert result.created is True
    assert result.account.business_name == "Acme Ltd"
    assert len(store.accounts) == 1
    assert store.memberships[0].account_id == result.account.id
    assert store.memberships[0].role == "owner"
    assert store.subscriptions[0].plan == "pro"


def test_different_businesses_get_different_accounts():
    store = InMemoryStore()
    first = signup(store, "a@example.com", "TX100", "Acme Ltd")
    second = signup(store, "b@example.com", "TX200", "Beta Ltd")
    assert first.account.id != second.account.id
    assert len(store.accounts) == 2
    assert len(store.subscriptions) == 2


def test_store_failure_propagates():
    store = InMemoryStore()
    store.fail_on("subscription")
    with pytest.raises(StoreError):
        signup(store, "owner@example.com", "TX100", "Acme Ltd")
