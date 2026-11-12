"""Self-registration of a business account."""

from dataclasses import dataclass

from .store import Account, DuplicateError, InMemoryStore


class ConflictError(Exception):
    """The same registration key was reused with different business data."""


@dataclass(frozen=True)
class SignupResult:
    account: Account
    created: bool


def _normalise_email(value: str) -> str:
    email = value.strip().lower()
    if not email or "@" not in email:
        raise ValueError("owner_email must be a non-empty address")
    return email


def _normalise_tax_id(value: str) -> str:
    tax_id = "".join(ch for ch in value if not ch.isspace() and ch != "-").upper()
    if not tax_id:
        raise ValueError("tax_id must not be empty")
    return tax_id


def _name_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def signup(
    store: InMemoryStore,
    owner_email: str,
    tax_id: str,
    business_name: str,
    plan: str = "trial",
) -> SignupResult:
    """Register a business: account, owner membership, subscription.

    Idempotent per (normalised owner_email, normalised tax_id). Every step is
    "find or create", so a retry after a partial failure completes only the
    missing steps. Losing a race (DuplicateError) is treated as "already done".
    """
    email = _normalise_email(owner_email)
    tax = _normalise_tax_id(tax_id)
    name = " ".join(business_name.split())
    if not name:
        raise ValueError("business_name must not be empty")

    created = False
    account = store.find_account(email, tax)
    if account is None:
        try:
            account = store.create_account(email, tax, name)
            created = True
        except DuplicateError:
            account = store.find_account(email, tax)
            assert account is not None
    if _name_key(account.business_name) != _name_key(name):
        raise ConflictError("registration key is already used by another business")

    if store.find_membership(account.id) is None:
        try:
            store.create_membership(account.id, email)
            created = True
        except DuplicateError:
            pass

    if store.find_subscription(account.id) is None:
        try:
            store.create_subscription(account.id, plan)
            created = True
        except DuplicateError:
            pass

    return SignupResult(account=account, created=created)
