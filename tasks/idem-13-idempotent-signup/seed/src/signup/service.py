"""Self-registration of a business account."""

from dataclasses import dataclass

from .store import Account, InMemoryStore


class ConflictError(Exception):
    """The same registration key was reused with different business data."""


@dataclass(frozen=True)
class SignupResult:
    account: Account
    created: bool


def signup(
    store: InMemoryStore,
    owner_email: str,
    tax_id: str,
    business_name: str,
    plan: str = "trial",
) -> SignupResult:
    """Register a business: account, owner membership, subscription."""
    account = store.create_account(owner_email, tax_id, business_name)
    store.create_membership(account.id, owner_email)
    store.create_subscription(account.id, plan)
    return SignupResult(account=account, created=True)
