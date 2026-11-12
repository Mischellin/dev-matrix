import pytest
from docsvc import (
    AuditLog,
    Conflict,
    Document,
    DocumentRepository,
    DocumentService,
    InvalidTransition,
    NotFound,
    User,
)

ADMIN = User("root", "admin")
ALICE = User("alice")
BOB = User("bob")


@pytest.fixture
def env():
    repo = DocumentRepository()
    audit = AuditLog()
    repo.add(Document("d1", "Plan", "text", assignees={"alice"}))
    return repo, audit, DocumentService(repo, audit)


def snapshot(repo, doc_id="d1"):
    doc = repo.get(doc_id)
    assert doc is not None
    return (doc.title, doc.body, doc.status, doc.version, frozenset(doc.assignees))


def test_get_foreign_is_not_found(env) -> None:
    _, _, svc = env
    with pytest.raises(NotFound):
        svc.get(BOB, "d1")


def test_update_foreign_and_missing_both_not_found(env) -> None:
    _, _, svc = env
    with pytest.raises(NotFound) as foreign:
        svc.update(BOB, "d1", title="x")
    with pytest.raises(NotFound) as missing:
        svc.update(BOB, "nope", title="x")
    assert type(foreign.value) is type(missing.value)
    text = str(foreign.value).lower()
    for word in ("forbidden", "denied", "permission", "not allowed"):
        assert word not in text


def test_update_denied_has_no_side_effects(env) -> None:
    repo, audit, svc = env
    before = snapshot(repo)
    with pytest.raises(NotFound):
        svc.update(BOB, "d1", title="hacked", body="hacked")
    assert snapshot(repo) == before
    assert audit.entries == []


def test_delete_foreign_is_not_found_and_keeps_document(env) -> None:
    repo, audit, svc = env
    with pytest.raises(NotFound):
        svc.delete(BOB, "d1")
    assert repo.ids() == ["d1"]
    assert audit.entries == []


def test_delete_missing_is_not_found(env) -> None:
    _, _, svc = env
    with pytest.raises(NotFound):
        svc.delete(ADMIN, "nope")


def test_transition_foreign_is_not_found_without_side_effects(env) -> None:
    repo, audit, svc = env
    before = snapshot(repo)
    with pytest.raises(NotFound):
        svc.transition(BOB, "d1", "review")
    assert snapshot(repo) == before
    assert audit.entries == []


def test_transition_foreign_and_missing_indistinguishable(env) -> None:
    _, _, svc = env
    # Even a transition that would be invalid must not leak existence.
    with pytest.raises(NotFound):
        svc.transition(BOB, "d1", "archived")
    with pytest.raises(NotFound):
        svc.transition(BOB, "nope", "archived")


def test_stale_version_from_unauthorized_actor_is_not_found(env) -> None:
    repo, audit, svc = env
    before = snapshot(repo)
    with pytest.raises(NotFound):
        svc.update(BOB, "d1", title="x", expected_version=99)
    with pytest.raises(NotFound):
        svc.transition(BOB, "d1", "review", expected_version=99)
    assert snapshot(repo) == before
    assert audit.entries == []


def test_stale_version_for_authorized_actor_is_conflict(env) -> None:
    repo, audit, svc = env
    before = snapshot(repo)
    with pytest.raises(Conflict):
        svc.update(ALICE, "d1", title="x", expected_version=5)
    with pytest.raises(Conflict):
        svc.transition(ADMIN, "d1", "review", expected_version=5)
    assert snapshot(repo) == before
    assert audit.entries == []


def test_authorized_actors_succeed_and_are_audited(env) -> None:
    repo, audit, svc = env
    with pytest.raises(NotFound):
        svc.update(BOB, "d1", body="nope")
    svc.update(ALICE, "d1", body="new", expected_version=1)
    svc.transition(ADMIN, "d1", "review", expected_version=2)
    svc.delete(ALICE, "d1")
    assert repo.get("d1") is None
    assert [(e.actor_id, e.action, e.doc_id) for e in audit.entries] == [
        ("alice", "update", "d1"),
        ("root", "transition", "d1"),
        ("alice", "delete", "d1"),
    ]


def test_invalid_transition_not_applied_and_not_audited(env) -> None:
    repo, audit, svc = env
    before = snapshot(repo)
    with pytest.raises(NotFound):
        svc.transition(BOB, "d1", "published")
    with pytest.raises(InvalidTransition):
        svc.transition(ALICE, "d1", "published")
    assert snapshot(repo) == before
    assert audit.entries == []


def test_failed_attempts_never_reach_audit_log(env) -> None:
    _, audit, svc = env
    for call in (
        lambda: svc.update(BOB, "d1", title="x"),
        lambda: svc.update(ADMIN, "nope", title="x"),
        lambda: svc.delete(BOB, "d1"),
        lambda: svc.update(ALICE, "d1", title="x", expected_version=9),
    ):
        with pytest.raises((NotFound, Conflict)):
            call()
    assert audit.entries == []
