# Security Task: Fix WebApp Auth Verification Allowing Future auth_date

## Context
In `src/auth/init_data.py`, `verify_init_data` validates Telegram WebApp `initData` parameters using HMAC-SHA256 signatures and checks timestamp freshness via `now - auth_date > max_age_seconds`.

## Vulnerability
If an attacker provides an `auth_date` far in the future, `now - auth_date` evaluates to a negative number, thus bypassing the freshness check completely. Because the HMAC signature is computed on the attacker's payload (with legitimate bot token or captured session), this defeats expiration protection.

## Requirements
1. If `auth_date` is in the future beyond allowable clock skew, raise `InitDataValidationError` with the word `"future"` in the error message.
2. Introduce a new optional keyword parameter `max_future_skew_seconds: int = 60` to `verify_init_data`.
3. If `auth_date` is in the future but within `max_future_skew_seconds` (e.g. +5 seconds due to slight server-client clock drift), it must be accepted as valid.
4. Existing functionality (hash verification, `max_age_seconds` expiration, field parsing) must not be broken.

## Definition of Done
All existing tests pass, and new tests demonstrate that far-future timestamps are rejected while acceptable clock skews succeed.
