# Bugfix Task: Derive Gateway Permissions from Role Claims, Not from OAuth Scope

## Context
`src/gateway/permissions.py` converts the claims of an already verified access token (issued by the identity provider) into a list of permissions for one project. `derive_permissions(claims, project)` returns the permissions and `is_allowed(claims, project, permission)` checks a single one.

The identity provider publishes authorization data in two claims:
- `project_roles`: a mapping `project id -> list of role names` (e.g. `{"alpha": ["editor"], "beta": ["viewer"]}`);
- `roles`: a flat list of role names that applies to every project (used by older tokens and as a fallback).

## Problem
The current implementation ignores both claims and builds permissions from the OAuth `scope` string instead. Scope only describes what the client application asked for, not what the user is allowed to do. As a result a token with a broad scope but no roles gets elevated rights, and a token carrying proper roles but a narrow scope is denied.

## Requirements
1. Permissions come only from roles, through this table (role names are case-sensitive):
   - `viewer`  -> `docs:read`
   - `editor`  -> `docs:read`, `docs:write`
   - `admin`   -> `docs:read`, `docs:write`, `docs:delete`, `members:manage`
   - `billing` -> `billing:read`, `billing:manage`
2. The `scope` claim must never grant (or remove) any permission, whatever it contains or whether it is present.
3. Role selection for `project`: if `project_roles` is a mapping and contains an entry for `project` that is a list, use exactly that list (an empty list means no roles and no fallback). Otherwise (claim missing, not a mapping, no entry for the project, or the entry is not a list) fall back to the flat `roles` claim. Roles of other projects must never leak into the result.
4. Role names that are not in the table are ignored, as are list items that are not strings. A `roles` claim that is not a list is treated as empty.
5. The result is the union of the permissions of all selected roles, without duplicates, as a list sorted alphabetically. No roles means an empty list.
6. `is_allowed` returns `True` only if the permission is in the derived list. Neither function may raise on malformed claims or modify the claims passed in.
7. Keep the public names `derive_permissions`, `is_allowed` and the `ROLE_PERMISSIONS` table exported from `gateway`.

## Definition of Done
All existing tests pass, and new tests show that scope has no influence on permissions, that project roles and the flat fallback behave as described, and that malformed claims are handled without errors.
