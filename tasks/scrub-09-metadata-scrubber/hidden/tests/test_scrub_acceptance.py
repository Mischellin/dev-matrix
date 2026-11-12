import copy

from pipeline import REDACTED, scrub_event, scrub_metadata


def test_nested_dicts_are_scrubbed() -> None:
    meta = {"request": {"headers": {"authorization": "Bearer x", "accept": "*/*"}}}
    assert scrub_metadata(meta) == {
        "request": {"headers": {"authorization": REDACTED, "accept": "*/*"}}
    }


def test_lists_and_tuples_are_traversed_and_types_kept() -> None:
    meta = {
        "items": [{"token": "t1", "n": 1}, "plain", 3],
        "pair": ({"secret": "s"}, [{"password": "p"}]),
    }
    result = scrub_metadata(meta)
    assert result == {
        "items": [{"token": REDACTED, "n": 1}, "plain", 3],
        "pair": ({"secret": REDACTED}, [{"password": REDACTED}]),
    }
    assert isinstance(result["items"], list)
    assert isinstance(result["pair"], tuple)
    assert isinstance(result["pair"][1], list)


def test_keys_match_case_insensitively() -> None:
    result = scrub_metadata({"PassWord": "a", "API_KEY": "b", "Token": "c"})
    assert set(result.values()) == {REDACTED}
    assert set(result) == {"PassWord", "API_KEY", "Token"}


def test_keys_match_by_substring() -> None:
    meta = {
        "X-Authorization-Header": "a",
        "db_password_old": "b",
        "refresh_token_v2": "c",
        "my_api_key": "d",
        "client_secret": "e",
        "username": "kept",
    }
    result = scrub_metadata(meta)
    assert result.pop("username") == "kept"
    assert set(result.values()) == {REDACTED}


def test_sensitive_key_redacts_whole_subtree() -> None:
    meta = {"secret": {"a": 1, "b": [1, 2]}, "token": ["x"], "password": None}
    assert scrub_metadata(meta) == {
        "secret": REDACTED,
        "token": REDACTED,
        "password": REDACTED,
    }


def test_input_is_not_mutated_and_nothing_is_shared() -> None:
    meta = {"a": {"password": "p", "list": [{"token": "t"}]}, "b": ({"k": [1]},)}
    snapshot = copy.deepcopy(meta)
    result = scrub_metadata(meta)
    assert meta == snapshot
    assert result["a"] is not meta["a"]
    assert result["a"]["list"] is not meta["a"]["list"]
    assert result["a"]["list"][0] is not meta["a"]["list"][0]
    assert result["b"][0]["k"] is not meta["b"][0]["k"]


def test_non_string_keys_are_kept_and_values_traversed() -> None:
    meta = {1: {"token": "t", "ok": 1}, None: "n", (1, 2): [{"secret": "s"}]}
    assert scrub_metadata(meta) == {
        1: {"token": REDACTED, "ok": 1},
        None: "n",
        (1, 2): [{"secret": REDACTED}],
    }


def test_non_sensitive_data_and_scalar_types_preserved() -> None:
    meta = {"i": 1, "f": 2.5, "b": True, "n": None, "s": "text", "l": [1, "a", None]}
    result = scrub_metadata(meta)
    assert result == meta
    assert type(result["b"]) is bool
    assert type(result["i"]) is int


def test_cycles_do_not_crash() -> None:
    meta: dict = {"name": "loop", "password": "p"}
    meta["self"] = meta
    child: list = [1]
    child.append(child)
    meta["child"] = child
    result = scrub_metadata(meta)
    assert result["name"] == "loop"
    assert result["password"] == REDACTED
    assert result["self"] == REDACTED
    assert result["child"][0] == 1
    assert result["child"][1] == REDACTED


def test_shared_reference_is_not_a_cycle() -> None:
    shared = {"token": "t", "v": 1}
    result = scrub_metadata({"a": shared, "b": [shared, shared]})
    expected = {"token": REDACTED, "v": 1}
    assert result == {"a": expected, "b": [expected, expected]}


def test_max_depth_redacts_everything_below_limit() -> None:
    meta = {"a": {"b": {"c": {"d": 1}}}, "x": 1}
    assert scrub_metadata(meta, max_depth=1) == {"a": {"b": REDACTED}, "x": 1}
    assert scrub_metadata(meta, max_depth=2) == {"a": {"b": {"c": REDACTED}}, "x": 1}
    assert scrub_metadata(meta, max_depth=3) == {
        "a": {"b": {"c": {"d": REDACTED}}},
        "x": 1,
    }
    assert scrub_metadata(meta, max_depth=4) == meta
    deep: dict = {}
    node = deep
    for _ in range(50):
        node["n"] = {}
        node = node["n"]
    assert scrub_metadata(deep, max_depth=100) == deep


def test_scrub_event_passes_options_and_leaves_other_fields() -> None:
    event = {
        "id": 1,
        "tags": ["a"],
        "metadata": {"Card_PIN": "1234", "inner": {"token": "t"}},
    }
    snapshot = copy.deepcopy(event)
    result = scrub_event(event, patterns=("pin",), max_depth=5)
    assert result == {
        "id": 1,
        "tags": ["a"],
        "metadata": {"Card_PIN": REDACTED, "inner": {"token": "t"}},
    }
    assert event == snapshot
    assert result is not event
    assert scrub_event({"id": 2, "metadata": None}) == {"id": 2, "metadata": None}
    assert scrub_event({"id": 3}) == {"id": 3}
