import hashlib
import hmac
import json
import time
import urllib.parse

import pytest
from auth.init_data import InitDataValidationError, verify_init_data

BOT_TOKEN = "123456:ABC-DEF1234ghikl"
USER = {"id": 12345, "first_name": "Test", "username": "testuser"}


def make_init_data(bot_token: str, user: dict, auth_date: int | None = None) -> str:
    if auth_date is None:
        auth_date = int(time.time())

    data = {
        "query_id": "AAHdF6AAAAAA",
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(auth_date),
        "hash": "",
    }

    check_parts = []
    for key in sorted(data.keys()):
        if key == "hash":
            continue
        check_parts.append(f"{key}={data[key]}")
    check_string = "\n".join(check_parts)

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    data["hash"] = computed_hash

    return urllib.parse.urlencode(data)


def test_far_future_auth_date_fails() -> None:
    future_auth = int(time.time()) + 100000
    raw = make_init_data(BOT_TOKEN, USER, auth_date=future_auth)
    with pytest.raises(InitDataValidationError, match="future"):
        verify_init_data(raw, bot_token=BOT_TOKEN)


def test_small_future_skew_allowed_by_default() -> None:
    # +5 seconds should pass default 60s window
    slightly_future = int(time.time()) + 5
    raw = make_init_data(BOT_TOKEN, USER, auth_date=slightly_future)
    result = verify_init_data(raw, bot_token=BOT_TOKEN)
    assert result.telegram_user_id == 12345


def test_custom_max_future_skew_respected() -> None:
    # +15 seconds should fail if max_future_skew_seconds is 10
    skewed_15s = int(time.time()) + 15
    raw = make_init_data(BOT_TOKEN, USER, auth_date=skewed_15s)
    with pytest.raises(InitDataValidationError, match="future"):
        verify_init_data(raw, bot_token=BOT_TOKEN, max_future_skew_seconds=10)

    # +15 seconds should pass if max_future_skew_seconds is 20
    res = verify_init_data(raw, bot_token=BOT_TOKEN, max_future_skew_seconds=20)
    assert res.telegram_user_id == 12345
