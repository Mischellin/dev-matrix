"""In-memory storage for documents and the audit log."""

from __future__ import annotations

import copy
from dataclasses import dataclass

from .models import Document


class DocumentRepository:
    """Stores documents; reads and writes work on copies."""

    def __init__(self) -> None:
        self._docs: dict[str, Document] = {}

    def add(self, doc: Document) -> None:
        if doc.id in self._docs:
            raise ValueError(f"duplicate document id: {doc.id}")
        self._docs[doc.id] = copy.deepcopy(doc)

    def get(self, doc_id: str) -> Document | None:
        doc = self._docs.get(doc_id)
        return copy.deepcopy(doc) if doc is not None else None

    def save(self, doc: Document) -> None:
        self._docs[doc.id] = copy.deepcopy(doc)

    def delete(self, doc_id: str) -> bool:
        return self._docs.pop(doc_id, None) is not None

    def ids(self) -> list[str]:
        return sorted(self._docs)


@dataclass(frozen=True)
class AuditEntry:
    actor_id: str
    action: str  # "update", "delete" or "transition"
    doc_id: str


class AuditLog:
    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []

    def record(self, actor_id: str, action: str, doc_id: str) -> None:
        self.entries.append(AuditEntry(actor_id, action, doc_id))
