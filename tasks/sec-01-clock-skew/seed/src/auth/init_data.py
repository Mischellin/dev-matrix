"""Telegram WebApp initData verification.

Algorithm: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
from dataclasses import dataclass


class InitDataValidationError(ValueError):
    """Invalid or tampered initData."""


@dataclass(frozen=True)
class VerifiedInitData:
    telegram_user_id: int
    first_name: str | None
    last_name: str | None
    username: str | None
    language_code: str | None
    auth_date: int  # Unix timestamp


def verify_init_data(
    init_data_raw: str,
    *,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> VerifiedInitData:
    """Verify Telegram WebApp initData and return verified user data.

    Raises InitDataValidationError if invalid, tampered, or expired.
    """
    if not init_data_raw or not bot_token:
        raise InitDataValidationError("Missing initData or bot token")

    parsed = urllib.parse.parse_qs(init_data_raw)
    data: dict[str, str] = {}
    for k, v in parsed.items():
        if isinstance(v, list) and len(v) == 1:
            data[k] = v[0]
        else:
            data[k] = str(v)

    received_hash = data.get("hash", "")
    if not received_hash:
        raise InitDataValidationError("Missing hash in initData")

    # Build check string: sorted key=value pairs, skip "hash"
    check_parts = []
    for key in sorted(data.keys()):
        if key == "hash":
            continue
        value = data[key]
        check_parts.append(f"{key}={value}")
    check_string = "\n".join(check_parts)

    # Compute secret key: HMAC_SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256,
    ).digest()

    computed_hash = hmac.new(
        secret_key, check_string.encode(), hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InitDataValidationError(
            "Invalid initData hash — data may be tampered"
        )

    # Validate auth_date freshness
    auth_date_str = data.get("auth_date", "")
    try:
        auth_date = int(auth_date_str)
    except (ValueError, TypeError):
        raise InitDataValidationError("Invalid auth_date in initData")

    now = int(time.time())
    if now - auth_date > max_age_seconds:
        raise InitDataValidationError("initData auth_date expired")

    # Parse user
    user_raw = data.get("user", "")
    if not user_raw:
        raise InitDataValidationError("Missing user in initData")

    try:
        user_data = json.loads(user_raw)
    except json.JSONDecodeError:
        raise InitDataValidationError("Invalid user JSON in initData")

    telegram_user_id = user_data.get("id")
    if not telegram_user_id or not isinstance(telegram_user_id, int):
        raise InitDataValidationError("Missing or invalid user id in initData")

    return VerifiedInitData(
        telegram_user_id=telegram_user_id,
        first_name=user_data.get("first_name"),
        last_name=user_data.get("last_name"),
        username=user_data.get("username"),
        language_code=user_data.get("language_code"),
        auth_date=auth_date,
    )
