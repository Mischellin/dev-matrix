"""Domain objects and errors of the document service."""

from __future__ import annotations

from dataclasses import dataclass, field

STATUSES = ("draft", "review", "published", "archived")
TRANSITIONS = {
    "draft": {"review"},
    "review": {"draft", "published"},
    "published": {"archived"},
    "archived": set(),
}


class NotFound(Exception):
    """The document does not exist (or the caller may not know that it does)."""


class Forbidden(Exception):
    """The caller is not allowed to perform the action."""


class Conflict(Exception):
    """The expected version does not match the stored version."""


class InvalidTransition(Exception):
    """The requested status change is not allowed by the workflow."""


@dataclass(frozen=True)
class User:
    id: str
    role: str = "employee"  # "admin" or "employee"


@dataclass
class Document:
    id: str
    title: str
    body: str = ""
    status: str = "draft"
    version: int = 1
    assignees: set[str] = field(default_factory=set)
