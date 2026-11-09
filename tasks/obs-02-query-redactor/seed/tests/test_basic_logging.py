import logging

from logging_filter.filters import RedactQuerySecretsFilter


def test_filter_instantiates_and_passes_records() -> None:
    f = RedactQuerySecretsFilter()
    rec = logging.LogRecord("app", logging.INFO, "app.py", 1, "Normal message", (), None)
    assert f.filter(rec) is True
