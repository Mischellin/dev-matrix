from pipeline import REDACTED, scrub_event, scrub_metadata


def test_top_level_sensitive_key_is_redacted() -> None:
    result = scrub_metadata({"password": "hunter2", "page": "/home"})
    assert result == {"password": REDACTED, "page": "/home"}


def test_input_is_not_mutated_at_top_level() -> None:
    original = {"token": "abc", "page": "/home"}
    scrub_metadata(original)
    assert original == {"token": "abc", "page": "/home"}


def test_scrub_event_keeps_other_fields() -> None:
    event = {"id": 7, "name": "click", "metadata": {"secret": "x", "button": "ok"}}
    result = scrub_event(event)
    assert result == {
        "id": 7,
        "name": "click",
        "metadata": {"secret": REDACTED, "button": "ok"},
    }
    assert event["metadata"]["secret"] == "x"
