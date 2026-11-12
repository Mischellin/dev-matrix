import pytest
from docsvc import (
    AuditLog,
    Document,
    DocumentRepository,
    DocumentService,
    NotFound,
    User,
)

ADMIN = User("root", "admin")
ALICE = User("alice")


@pytest.fixture
def env():
    repo = DocumentRepository()
    audit = AuditLog()
    repo.add(Document("d1", "Plan", "text", assignees={"alice"}))
    return repo, audit, DocumentService(repo, audit)


def test_assigned_employee_reads_and_updates(env) -> None:
    repo, _, svc = env
    assert svc.get(ALICE, "d1").title == "Plan"
    doc = svc.update(ALICE, "d1", title="Plan v2")
    assert doc.title == "Plan v2"
    assert doc.version == 2
    assert repo.get("d1").title == "Plan v2"


def test_unassigned_employee_cannot_read(env) -> None:
    _, _, svc = env
    with pytest.raises(NotFound):
        svc.get(User("bob"), "d1")


def test_admin_can_transition(env) -> None:
    repo, _, svc = env
    svc.transition(ADMIN, "d1", "review")
    assert repo.get("d1").status == "review"
