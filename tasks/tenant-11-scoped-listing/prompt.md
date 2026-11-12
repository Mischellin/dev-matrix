# Security Task: Fix Document Listing Leaking Data Outside the User's Client Scope

## Context
`src/docsvc/listing.py` implements `DocumentService`, the read side of a multi-client document service. Staff members work on behalf of client companies and every document belongs to exactly one `client_id`. Visibility depends on the role of the `User`:
- `admin`: all clients.
- `manager`: the clients of their team (`team_clients[user.team_id]`).
- `employee`: only the clients explicitly assigned to them (`assignments[user.id]`).

`list_documents(user, *, status=None, client_id=None, limit=20, offset=0)` returns a `Page(items, total, limit, offset)`, and `get_document(user, document_id)` returns a single `Document`.

## Problem
The listing was written around the employee case only:
- `total` is computed before the scope is applied, so an employee learns how many documents exist for clients they cannot see, while `items` is correctly filtered.
- Managers and any unknown role fall through to "no restriction" and see every client.
- Ordering by `created_at` alone is unstable for equal timestamps, so pages can repeat or skip documents.
- `limit` and `offset` are not validated (negative values, zero, huge pages, non-integers).
- `get_document` reveals through its error message that a forbidden document exists and which client owns it.

## Requirements
1. Scope rules: `admin` sees all documents; `manager` sees documents of clients in `team_clients[user.team_id]` (a manager with `team_id=None` or an unknown team sees nothing; personal `assignments` are irrelevant to managers); `employee` sees documents of clients in `assignments[user.id]` (a user without an entry sees nothing).
2. A user with any other role must get `AccessDeniedError` from both `list_documents` and `get_document`.
3. `Page.total` must equal the number of documents in the full, unpaginated result set after applying scope, `status` and `client_id` filters. It must not depend on `limit` or `offset`; an `offset` past the end returns empty `items` with the correct `total`.
4. Filters are combined with the scope by intersection: `status` (one of `draft`, `review`, `approved`, `archived`) and `client_id` can only narrow the result. Asking for a `client_id` outside the user's scope returns an empty page with `total == 0`, not an error and not a count.
5. Ordering is deterministic: `created_at` descending, ties broken by `id` descending.
6. Validation, applied for every role before any data is read: `limit` must be an `int` (not `bool`) in `1..100`, `offset` an `int` (not `bool`) `>= 0`, and `status`, when given, must be a known status. Violations raise `ListingError`.
7. `get_document` raises `NotFoundError` both for a missing document and for one outside the user's scope. The error message must not contain the client id, the title or any other data of the requested document, and a forbidden document must be indistinguishable from a missing one by exception type.
8. Public names (`User`, `Document`, `Page`, `DocumentService`, `ListingError`, `AccessDeniedError`, `NotFoundError`) and the constructor signature stay unchanged.

## Definition of Done
All existing tests pass, and new tests demonstrate correct scoping of items and totals per role, filter combinations, pagination and ordering, parameter validation, and that `get_document` does not leak information about foreign documents.
