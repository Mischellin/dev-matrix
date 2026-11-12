import pytest
from docsvc import Document, DocumentService, NotFoundError, User

DOCS = [
    Document(1, "c-alpha", "Invoice A", "draft", 100),
    Document(2, "c-beta", "Invoice B", "approved", 200),
    Document(3, "c-gamma", "Contract C", "approved", 300),
    Document(4, "c-alpha", "Report A", "review", 400),
]
ASSIGN = {"emp-1": {"c-alpha"}}
TEAMS = {"t1": {"c-alpha", "c-beta"}}


@pytest.fixture
def svc() -> DocumentService:
    return DocumentService(DOCS, ASSIGN, TEAMS)


def test_admin_sees_everything_newest_first(svc: DocumentService) -> None:
    page = svc.list_documents(User("adm", "admin"))
    assert [d.id for d in page.items] == [4, 3, 2, 1]
    assert page.total == 4


def test_employee_sees_assigned_client_documents(svc: DocumentService) -> None:
    page = svc.list_documents(User("emp-1", "employee"))
    assert [d.id for d in page.items] == [4, 1]


def test_status_filter_for_admin(svc: DocumentService) -> None:
    page = svc.list_documents(User("adm", "admin"), status="approved")
    assert [d.id for d in page.items] == [3, 2]
    assert page.total == 2


def test_employee_can_get_own_document(svc: DocumentService) -> None:
    assert svc.get_document(User("emp-1", "employee"), 1).title == "Invoice A"
    with pytest.raises(NotFoundError):
        svc.get_document(User("emp-1", "employee"), 999)
