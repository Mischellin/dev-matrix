"""Service layer: access control, versioning and auditing for documents."""

from __future__ import annotations

from .models import (
    TRANSITIONS,
    Conflict,
    Document,
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

    def _load(self, actor: User, doc_id: str) -> Document:
        """Return the document or raise one and the same NotFound.

        A missing document and a document the actor may not access are
        indistinguishable to the caller. Nothing else runs before this check.
        """
        doc = self._repo.get(doc_id)
        if doc is None or not _can_access(actor, doc):
            raise NotFound(f"document {doc_id} not found")
        return doc

    @staticmethod
    def _check_version(doc: Document, expected_version: int | None) -> None:
        if expected_version is not None and doc.version != expected_version:
            raise Conflict(f"version mismatch for {doc.id}")

    def get(self, actor: User, doc_id: str) -> Document:
        return self._load(actor, doc_id)

    def update(
        self,
        actor: User,
        doc_id: str,
        *,
        title: str | None = None,
        body: str | None = None,
        expected_version: int | None = None,
    ) -> Document:
        doc = self._load(actor, doc_id)
        self._check_version(doc, expected_version)
        if title is not None:
            doc.title = title
        if body is not None:
            doc.body = body
        doc.version += 1
        self._repo.save(doc)
        self._audit.record(actor.id, "update", doc_id)
        return doc

    def delete(self, actor: User, doc_id: str) -> None:
        self._load(actor, doc_id)
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
        doc = self._load(actor, doc_id)
        self._check_version(doc, expected_version)
        if new_status not in TRANSITIONS.get(doc.status, set()):
            raise InvalidTransition(f"{doc.status} -> {new_status}")
        doc.status = new_status
        doc.version += 1
        self._repo.save(doc)
        self._audit.record(actor.id, "transition", doc_id)
        return doc
