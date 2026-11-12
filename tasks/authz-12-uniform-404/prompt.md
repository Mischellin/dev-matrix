# Security Task: Close the Document Existence Oracle in Update, Delete and Transition

## Context
`src/docsvc/service.py` implements `DocumentService`, a service layer over `DocumentRepository` for a small document system. Users are either `admin` or `employee`; an employee may access a document only if their id is in `document.assignees`. Mutating calls (`update`, `delete`, `transition`) append an entry to `AuditLog`. `get` already hides documents from unassigned employees by raising `NotFound`.

## Vulnerability
The mutating paths do not behave like `get`:
- For an existing document the caller may not access, they raise `Forbidden`, while a missing document raises `NotFound`. Any employee can therefore enumerate which document ids exist.
- `transition` applies and saves the change before checking access, so a denied caller still modifies the stored document.
- `update` checks `expected_version` before authorization, so a stale version reveals existence through `Conflict`, and it writes an audit entry before any check, so denied or failed attempts appear in the log as if they had happened.

## Requirements
1. For `get`, `update`, `delete` and `transition`, a missing document and a document the actor may not access must behave identically: both raise `NotFound`, and the message must not mention permissions (no "forbidden", "denied", "permission" or "not allowed"). `Forbidden` must no longer be raised by the service.
2. Authorization is evaluated first. A denied or missing-document call must perform no other check: a stale `expected_version` or an invalid status change from such a caller must still produce `NotFound`, not `Conflict` or `InvalidTransition`.
3. A denied call has no side effects: the stored document (title, body, status, version, assignees) is unchanged, a denied `delete` leaves the document in the repository, and nothing is written to the audit log.
4. Admins and assigned employees keep working as before: `update` and `transition` bump `version` by one and persist the change, `delete` removes the document.
5. For an authorized actor, a non-`None` `expected_version` that differs from the stored version raises `Conflict`; an invalid status change raises `InvalidTransition`. Neither modifies the document or writes an audit entry. `Conflict` is checked before `InvalidTransition`.
6. Audit entries (`actor_id`, `action` in `"update"`, `"delete"`, `"transition"`, `doc_id`) are recorded only for successful mutations, one per call, after the change is persisted.
7. Public names and signatures stay unchanged (`Forbidden` stays importable).

## Definition of Done
All existing tests pass, and new tests demonstrate that foreign and missing documents are indistinguishable for every operation, that denied calls leave repository and audit log untouched, and that authorized callers still succeed.
