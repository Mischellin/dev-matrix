# Bugfix Task: Make Business Self-Registration Idempotent and Retry-Safe

## Context
`signup.service.signup(store, owner_email, tax_id, business_name, plan="trial")` registers a business in a SaaS product. It performs three separate store operations in order: create the account, create the owner membership, create the subscription. It returns a `SignupResult(account, created)`. The in-memory store (`signup/store.py`, do not modify it) enforces uniqueness (one account per `(owner_email, tax_id)`, one owner membership and one subscription per account) by raising `DuplicateError`, and lets tests inject failures with `store.fail_on(step, times=1)` (raises `StoreError` in the next `create_<step>` calls) and `store.before(step, callback)` (runs `callback` once right before the next `create_<step>` call, simulating a concurrent request). Steps are `"account"`, `"membership"`, `"subscription"`. The store also has `find_account(owner_email, tax_id)`, `find_membership(account_id)` and `find_subscription(account_id)`.

## Problem
Clients retry registration requests (double clicks, timeouts, a failure between steps). Currently:
- A repeated call raises `DuplicateError`, or, when the e-mail or tax id differs only in formatting, silently creates a second account.
- A failure in the middle leaves a half-registered business (account without membership or subscription), and the retry cannot complete it.
- Reusing the same key for a different business is not detected.

## Requirements
1. Normalise inputs: `owner_email` is stripped and lower-cased; `tax_id` has all whitespace and `-` characters removed and is upper-cased; `business_name` has surrounding whitespace stripped and inner whitespace runs collapsed. Normalised values are what gets stored (accounts and memberships). The idempotency key is `(normalised owner_email, normalised tax_id)`.
2. Raise `ValueError`, before any write, if the normalised e-mail is empty or has no `@`, or if the normalised tax id or business name is empty.
3. A repeated call with the same key and the same business returns the existing account and creates no new records. The result has `created=False`.
4. Every step is "find or create": after a failure at any step (`StoreError` propagates to the caller), a retry creates only the records that are still missing, exactly once, and returns the same account. Such a retry returns `created=True`; `created` is `True` if and only if the call inserted at least one of the three records.
5. If the key already exists (fully or partially registered) but the business name differs, raise `ConflictError`, and do not create or change anything. Names are compared ignoring case and differences in whitespace.
6. A repeat call never changes the existing subscription: if the plan argument differs, the original plan is kept.
7. A request that loses a race (the store raises `DuplicateError` because another request created the record between the lookup and the insert) must not fail: treat the record as already existing and continue. The final state has exactly one account, one owner membership and one subscription for the key.
8. Different keys (e.g. the same e-mail with a different tax id) are independent accounts.

## Definition of Done
All existing tests pass, and new tests demonstrate idempotent repeats, retry after a failure at each step, conflict detection, normalisation and the interleaved-request case.
