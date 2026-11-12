"""Service layer: access control, versioning and auditing for documents."""

from __future__ import annotations

from .models import (
    TRANSITIONS,
    Conflict,
    Document,
    Forbidden,
    InvalidTransition,
    NotFound,
    User,
)
from .repository import AuditLog, DocumentRepository


def _can_access(actor: User, doc: Document) -> bool:
    return actor.role == "admin" or actor.id in doc.assignees


class DocumentService:
    def __init__(self, repo: DocumentRepository, audit: AuditLog) -> None:
        self._repo = repo
        self._audit = audit

    def _load(self, doc_id: str) -> Document:
        doc = self._repo.get(doc_id)
        if doc is None:
            raise NotFound(f"document {doc_id} not found")
        return doc

    def get(self, actor: User, doc_id: str) -> Document:
        doc = self._load(doc_id)
        if not _can_access(actor, doc):
            raise NotFound(f"document {doc_id} not found")
        return doc

    def update(
        self,
        actor: User,
        doc_id: str,
        *,
        title: str | None = None,
        body: str | None = None,
        expected_version: int | None = None,
    ) -> Document:
        doc = self._load(doc_id)
        self._audit.record(actor.id, "update", doc_id)
        if expected_version is not None and doc.version != expected_version:
            raise Conflict(f"version mismatch for {doc_id}")
        if not _can_access(actor, doc):
            raise Forbidden("not allowed to modify this document")
        if title is not None:
            doc.title = title
        if body is not None:
            doc.body = body
        doc.version += 1
        self._repo.save(doc)
        return doc

    def delete(self, actor: User, doc_id: str) -> None:
        doc = self._load(doc_id)
        if not _can_access(actor, doc):
            raise Forbidden("not allowed to delete this document")
        self._repo.delete(doc_id)
        self._audit.record(actor.id, "delete", doc_id)

    def transition(
        self,
        actor: User,
        doc_id: str,
        new_status: str,
        *,
        expected_version: int | None = None,
    ) -> Document:
        doc = self._load(doc_id)
        if expected_version is not None and doc.version != expected_version:
            raise Conflict(f"version mismatch for {doc_id}")
        if new_status not in TRANSITIONS.get(doc.status, set()):
            raise InvalidTransition(f"{doc.status} -> {new_status}")
        # Apply first, check access afterwards.
        doc.status = new_status
        doc.version += 1
        self._repo.save(doc)
        if not _can_access(actor, doc):
            raise Forbidden("not allowed to change this document")
        self._audit.record(actor.id, "transition", doc_id)
        return doc
