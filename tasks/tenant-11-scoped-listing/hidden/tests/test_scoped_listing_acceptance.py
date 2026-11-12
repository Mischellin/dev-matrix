import pytest
from docsvc import (
    AccessDeniedError,
    Document,
    DocumentService,
    ListingError,
    NotFoundError,
    User,
)

DOCS = [
    Document(1, "c-alpha", "Alpha invoice", "draft", 100),
    Document(2, "c-beta", "Beta invoice", "approved", 200),
    Document(3, "c-gamma", "Gamma secret contract", "approved", 300),
    Document(4, "c-alpha", "Alpha report", "review", 400),
    Document(5, "c-delta", "Delta secret plan", "draft", 400),
    Document(6, "c-gamma", "Gamma memo", "draft", 500),
    Document(7, "c-alpha", "Alpha contract", "approved", 600),
    Document(8, "c-beta", "Beta memo", "draft", 600),
]
ASSIGN = {"emp-1": {"c-alpha", "c-gamma"}, "emp-2": set()}
TEAMS = {"t1": {"c-alpha", "c-beta"}, "t2": {"c-delta"}}

ADMIN = User("adm", "admin")
MANAGER = User("mgr-1", "manager", team_id="t1")
EMP1 = User("emp-1", "employee")


@pytest.fixture
def svc() -> DocumentService:
    return DocumentService(DOCS, ASSIGN, TEAMS)


def ids(page) -> list[int]:
    return [d.id for d in page.items]


def test_employee_total_counts_only_visible_documents(svc) -> None:
    page = svc.list_documents(EMP1)
    assert ids(page) == [7, 6, 4, 3, 1]
    assert page.total == 5


def test_employee_total_with_status_filter(svc) -> None:
    page = svc.list_documents(EMP1, status="draft")
    assert ids(page) == [6, 1]
    assert page.total == 2


def test_manager_sees_only_team_clients(svc) -> None:
    page = svc.list_documents(MANAGER)
    assert ids(page) == [8, 7, 4, 2, 1]
    assert page.total == 5


def test_manager_ignores_personal_assignments_and_other_teams(svc) -> None:
    other = User("mgr-2", "manager", team_id="t2")
    page = svc.list_documents(other)
    assert ids(page) == [5]
    assert page.total == 1
    # manager without a team, or with an unknown team, sees nothing
    for mgr in (User("mgr-3", "manager"), User("mgr-4", "manager", team_id="nope")):
        page = svc.list_documents(mgr)
        assert page.items == []
        assert page.total == 0


def test_unassigned_employee_sees_nothing(svc) -> None:
    for user in (User("emp-2", "employee"), User("emp-unknown", "employee")):
        page = svc.list_documents(user)
        assert page.items == []
        assert page.total == 0


def test_pagination_total_is_unpaginated_count(svc) -> None:
    first = svc.list_documents(EMP1, limit=2, offset=0)
    second = svc.list_documents(EMP1, limit=2, offset=2)
    last = svc.list_documents(EMP1, limit=2, offset=4)
    assert (ids(first), ids(second), ids(last)) == ([7, 6], [4, 3], [1])
    assert first.total == second.total == last.total == 5
    assert (first.limit, second.offset) == (2, 2)


def test_ordering_is_newest_first_with_id_tiebreak(svc) -> None:
    page = svc.list_documents(ADMIN)
    assert ids(page) == [8, 7, 6, 5, 4, 3, 2, 1]
    assert svc.list_documents(ADMIN, limit=3, offset=3).items == page.items[3:6]


def test_offset_beyond_total_keeps_total(svc) -> None:
    page = svc.list_documents(EMP1, offset=50)
    assert page.items == []
    assert page.total == 5


def test_invalid_parameters_rejected_for_every_role(svc) -> None:
    bad = [
        {"limit": 0},
        {"limit": -1},
        {"limit": 101},
        {"limit": "10"},
        {"limit": True},
        {"offset": -1},
        {"offset": 1.5},
        {"status": "deleted"},
    ]
    for user in (ADMIN, MANAGER, EMP1):
        for kwargs in bad:
            with pytest.raises(ListingError):
                svc.list_documents(user, **kwargs)
        assert svc.list_documents(user, limit=100).limit == 100


def test_client_filter_cannot_widen_scope(svc) -> None:
    # c-delta is outside the employee's scope: empty page, no error, no leaked count
    page = svc.list_documents(EMP1, client_id="c-delta")
    assert page.items == []
    assert page.total == 0
    page = svc.list_documents(EMP1, client_id="c-gamma", status="draft")
    assert ids(page) == [6]
    assert page.total == 1
    # admin may filter by any client
    assert svc.list_documents(ADMIN, client_id="c-delta").total == 1


def test_unknown_role_is_denied(svc) -> None:
    with pytest.raises(AccessDeniedError):
        svc.list_documents(User("x", "guest"))
    with pytest.raises(AccessDeniedError):
        svc.get_document(User("x", "guest"), 1)


def test_get_document_does_not_leak_foreign_documents(svc) -> None:
    assert svc.get_document(EMP1, 3).title == "Gamma secret contract"
    assert svc.get_document(ADMIN, 5).client_id == "c-delta"
    with pytest.raises(NotFoundError) as foreign:
        svc.get_document(EMP1, 5)
    with pytest.raises(NotFoundError) as missing:
        svc.get_document(EMP1, 999)
    for text in (str(foreign.value), str(missing.value)):
        assert "c-delta" not in text
        assert "Delta" not in text
    # a foreign document is indistinguishable from a missing one
    assert type(foreign.value) is type(missing.value)
