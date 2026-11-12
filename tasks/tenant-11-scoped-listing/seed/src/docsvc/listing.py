"""Document listing for a service where staff work on behalf of client companies."""

from __future__ import annotations

from dataclasses import dataclass

STATUSES = ("draft", "review", "approved", "archived")


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
        if user.role == "employee":
            return set(self._assignments.get(user.id, set()))
        return None

    def list_documents(
        self,
        user: User,
        *,
        status: str | None = None,
        client_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Page:
        docs = [d for d in self._documents if status is None or d.status == status]
        if client_id is not None:
            docs = [d for d in docs if d.client_id == client_id]
        total = len(docs)
        scope = self._scope(user)
        if scope is not None:
            docs = [d for d in docs if d.client_id in scope]
        docs.sort(key=lambda d: d.created_at, reverse=True)
        return Page(items=docs[offset : offset + limit], total=total, limit=limit, offset=offset)

    def get_document(self, user: User, document_id: int) -> Document:
        for doc in self._documents:
            if doc.id == document_id:
                scope = self._scope(user)
                if scope is not None and doc.client_id not in scope:
                    raise NotFoundError(f"document {doc.id} belongs to client {doc.client_id}")
                return doc
        raise NotFoundError(f"document {document_id} not found")
