"""Document listing for a service where staff work on behalf of client companies."""

from __future__ import annotations

from dataclasses import dataclass

STATUSES = ("draft", "review", "approved", "archived")
MAX_LIMIT = 100


class ListingError(ValueError):
    """Invalid listing parameters."""


class AccessDeniedError(Exception):
    """The user's role is not allowed to read documents."""


class NotFoundError(LookupError):
    """The document does not exist or is not visible to the user."""


@dataclass(frozen=True)
class User:
    id: str
    role: str  # "admin" | "manager" | "employee"
    team_id: str | None = None


@dataclass(frozen=True)
class Document:
    id: int
    client_id: str
    title: str
    status: str
    created_at: int


@dataclass(frozen=True)
class Page:
    items: list[Document]
    total: int
    limit: int
    offset: int


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class DocumentService:
    def __init__(
        self,
        documents: list[Document],
        assignments: dict[str, set[str]],
        team_clients: dict[str, set[str]],
    ) -> None:
        # assignments: user id -> client ids; team_clients: team id -> client ids
        self._documents = list(documents)
        self._assignments = assignments
        self._team_clients = team_clients

    def _scope(self, user: User) -> set[str] | None:
        """Client ids the user may see, or None for "no restriction"."""
        if user.role == "admin":
            return None
        if user.role == "manager":
            if user.team_id is None:
                return set()
            return set(self._team_clients.get(user.team_id, set()))
        if user.role == "employee":
            return set(self._assignments.get(user.id, set()))
        raise AccessDeniedError("access denied")

    def _visible(self, user: User) -> list[Document]:
        scope = self._scope(user)
        if scope is None:
            return list(self._documents)
        return [d for d in self._documents if d.client_id in scope]

    def list_documents(
        self,
        user: User,
        *,
        status: str | None = None,
        client_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Page:
        if not _is_int(limit) or not 1 <= limit <= MAX_LIMIT:
            raise ListingError(f"limit must be an integer between 1 and {MAX_LIMIT}")
        if not _is_int(offset) or offset < 0:
            raise ListingError("offset must be a non-negative integer")
        if status is not None and status not in STATUSES:
            raise ListingError("unknown status")
        docs = self._visible(user)
        if status is not None:
            docs = [d for d in docs if d.status == status]
        if client_id is not None:
            docs = [d for d in docs if d.client_id == client_id]
        docs.sort(key=lambda d: (-d.created_at, -d.id))
        return Page(
            items=docs[offset : offset + limit], total=len(docs), limit=limit, offset=offset
        )

    def get_document(self, user: User, document_id: int) -> Document:
        for doc in self._visible(user):
            if doc.id == document_id:
                return doc
        raise NotFoundError("document not found")
