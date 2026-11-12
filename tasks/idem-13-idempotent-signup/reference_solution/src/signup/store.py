"""In-memory store with uniqueness constraints and injectable failure points."""

from collections.abc import Callable
from dataclasses import dataclass

STEPS = ("account", "membership", "subscription")


class StoreError(Exception):
    """Raised by the store when an operation fails (real or injected)."""


class DuplicateError(StoreError):
    """Raised when a uniqueness constraint of the store is violated."""


@dataclass(frozen=True)
class Account:
    id: int
    owner_email: str
    tax_id: str
    business_name: str


@dataclass(frozen=True)
class Membership:
    account_id: int
    email: str
    role: str


@dataclass(frozen=True)
class Subscription:
    account_id: int
    plan: str
    status: str


class InMemoryStore:
    """Stores accounts, memberships and subscriptions as plain lists.

    Constraints: one account per (owner_email, tax_id) pair, one owner
    membership per account, one subscription per account. Violations raise
    DuplicateError. Every create_* call first runs the hooks registered for
    its step, so tests can simulate failures and interleaved requests.
    """

    def __init__(self) -> None:
        self.accounts: list[Account] = []
        self.memberships: list[Membership] = []
        self.subscriptions: list[Subscription] = []
        self._failures: dict[str, int] = {}
        self._before: dict[str, list[Callable[[], None]]] = {}

    def fail_on(self, step: str, times: int = 1) -> None:
        """Make the next `times` create_<step> calls raise StoreError."""
        if step not in STEPS:
            raise ValueError(f"unknown step: {step}")
        self._failures[step] = times

    def before(self, step: str, callback: Callable[[], None]) -> None:
        """Run `callback` once, right before the next create_<step> call."""
        if step not in STEPS:
            raise ValueError(f"unknown step: {step}")
        self._before.setdefault(step, []).append(callback)

    def _enter(self, step: str) -> None:
        callbacks = self._before.pop(step, [])
        for callback in callbacks:
            callback()
        if self._failures.get(step, 0) > 0:
            self._failures[step] -= 1
            raise StoreError(f"injected failure at {step}")

    def find_account(self, owner_email: str, tax_id: str) -> Account | None:
        for account in self.accounts:
            if account.owner_email == owner_email and account.tax_id == tax_id:
                return account
        return None

    def find_membership(self, account_id: int) -> Membership | None:
        for membership in self.memberships:
            if membership.account_id == account_id and membership.role == "owner":
                return membership
        return None

    def find_subscription(self, account_id: int) -> Subscription | None:
        for subscription in self.subscriptions:
            if subscription.account_id == account_id:
                return subscription
        return None

    def create_account(self, owner_email: str, tax_id: str, business_name: str) -> Account:
        self._enter("account")
        if self.find_account(owner_email, tax_id) is not None:
            raise DuplicateError("account already exists")
        account = Account(len(self.accounts) + 1, owner_email, tax_id, business_name)
        self.accounts.append(account)
        return account

    def create_membership(self, account_id: int, email: str) -> Membership:
        self._enter("membership")
        if self.find_membership(account_id) is not None:
            raise DuplicateError("owner membership already exists")
        membership = Membership(account_id, email, "owner")
        self.memberships.append(membership)
        return membership

    def create_subscription(self, account_id: int, plan: str) -> Subscription:
        self._enter("subscription")
        if self.find_subscription(account_id) is not None:
            raise DuplicateError("subscription already exists")
        subscription = Subscription(account_id, plan, "active")
        self.subscriptions.append(subscription)
        return subscription
