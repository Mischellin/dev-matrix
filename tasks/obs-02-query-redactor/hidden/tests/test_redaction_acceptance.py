import logging

import pytest
from logging_filter.filters import RedactQuerySecretsFilter

_DL = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkb2MifQ.c2lnbmF0dXJl"
_PATH = f"/api/v1/documents/1f0e/download?dl={_DL}"
_ACCESS_FMT = '%s - "%s %s HTTP/%s" %d'


def _access_record(full_path: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=_ACCESS_FMT,
        args=("10.0.0.1:0", "GET", full_path, "1.1", 200),
        exc_info=None,
    )


def _scrubbed(full_path: str) -> str:
    rec = _access_record(full_path)
    assert RedactQuerySecretsFilter().filter(rec) is True
    return rec.getMessage()


def test_access_line_redacts_dl_token() -> None:
    out = _scrubbed(_PATH)
    assert _DL not in out
    assert '"GET /api/v1/documents/1f0e/download?dl=<redacted> HTTP/1.1" 200' in out


def test_mixed_parameters_only_sensitive_redacted() -> None:
    out = _scrubbed(f"/api/v1/documents/1f0e/preview?as=pdf&dl={_DL}&inline=1")
    assert out.count("<redacted>") == 1
    assert "?as=pdf&dl=<redacted>&inline=1" in out


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("?code=AUTHCODE123&state=STATE456", "?code=<redacted>&state=<redacted>"),
        (
            "?X-Amz-Credential=AKIA/x&X-Amz-Signature=abcdef",
            "?X-Amz-Credential=<redacted>&X-Amz-Signature=<redacted>",
        ),
        ("?token=abc.def&page=2", "?token=<redacted>&page=2"),
        ("?access_token=secret1&refresh_token=secret2", "?access_token=<redacted>&refresh_token=<redacted>"),
    ],
)
def test_other_secret_params_redacted(query: str, expected: str) -> None:
    assert expected in _scrubbed(f"/auth/callback{query}")


@pytest.mark.parametrize(
    "query",
    ["?status=new&download=1", "?code_type=x&dlx=1", "?limit=50&offset=0", ""],
)
def test_harmless_queries_unchanged(query: str) -> None:
    path = f"/api/v1/documents{query}"
    assert f'"GET {path} HTTP/1.1"' in _scrubbed(path)


def test_filter_is_idempotent() -> None:
    rec = _access_record(_PATH)
    f = RedactQuerySecretsFilter()
    assert f.filter(rec) is True
    msg1 = rec.getMessage()
    assert f.filter(rec) is True
    msg2 = rec.getMessage()
    assert msg1 == msg2


def test_dict_args_formatting_supported() -> None:
    f = RedactQuerySecretsFilter()
    rec = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="User %(user)s accessed %(url)s",
        args={"user": "alice", "url": "/docs?dl=secret_jwt&page=1"},
        exc_info=None,
    )
    assert f.filter(rec) is True
    assert rec.getMessage() == "User alice accessed /docs?dl=<redacted>&page=1"


def test_template_placeholder_in_query_does_not_break_formatting() -> None:
    f = RedactQuerySecretsFilter()
    rec = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="/docs?token=%s",
        args=("secret_session_token",),
        exc_info=None,
    )
    assert f.filter(rec) is True
    assert rec.getMessage() == "/docs?token=<redacted>"


def test_percent_encoded_parameter_names_redacted() -> None:
    # %74oken is 'token', %64l is 'dl'
    out = _scrubbed("/download?%74oken=secret_probe&%64l=my_file_dl&other=123")
    assert "secret_probe" not in out
    assert "my_file_dl" not in out
    assert "?%74oken=<redacted>&%64l=<redacted>&other=123" in out


def test_apostrophe_does_not_break_subsequent_secrets() -> None:
    # Query string with apostrophe before sensitive parameter
    out = _scrubbed("/docs?token=first'SECOND&state=THIRD")
    assert "first'SECOND" not in out
    assert "THIRD" not in out
    assert "?token=<redacted>&state=<redacted>" in out

    out2 = _scrubbed("/search?filter=john's&token=my_secret")
    assert "my_secret" not in out2
    assert "?filter=john's&token=<redacted>" in out2


def test_multiple_urls_in_single_message_scrubbed() -> None:
    # Multiple URLs in list representation without spaces
    text = "urls=['/a?page=1','/b?token=demo_secret']"
    f = RedactQuerySecretsFilter()
    rec = logging.LogRecord("test", logging.INFO, __file__, 1, text, (), None)
    assert f.filter(rec) is True
    out = rec.getMessage()
    assert "demo_secret" not in out
    assert "urls=['/a?page=1','/b?token=<redacted>']" in out


def test_uvicorn_access_formatter_unpacking_compatibility() -> None:
    # Emulate Uvicorn AccessFormatter unpacking: (client_addr, method, full_path, http_version, status_code)
    f = RedactQuerySecretsFilter()
    rec = _access_record(f"/api/v1/download?dl={_DL}")
    assert f.filter(rec) is True

    # AccessFormatter contract: record.args must remain unpackable tuple
    assert isinstance(rec.args, tuple)
    assert len(rec.args) == 5
    _client_addr, _method, full_path, _http_version, status_code = rec.args
    assert _DL not in full_path
    assert "?dl=<redacted>" in full_path
    assert status_code == 200


def test_comma_separated_filter_and_token_values() -> None:
    out1 = _scrubbed("/search?filter=a,b&token=REVIEW_MARKER")
    assert "REVIEW_MARKER" not in out1
    assert "?filter=a,b&token=<redacted>" in out1

    out2 = _scrubbed("/download?token=prefix,REVIEW_MARKER")
    assert "prefix,REVIEW_MARKER" not in out2
    assert "?token=<redacted>" in out2


def test_numeric_and_repr_format_specifiers_in_template() -> None:
    f = RedactQuerySecretsFilter()
    rec1 = logging.LogRecord("test", logging.INFO, __file__, 1, "/docs?code=%d", (123,), None)
    assert f.filter(rec1) is True
    assert rec1.getMessage() == "/docs?code=<redacted>"

    rec2 = logging.LogRecord("test", logging.INFO, __file__, 1, "/docs?token=%r", ("secret_token",), None)
    assert f.filter(rec2) is True
    assert "secret_token" not in rec2.getMessage()
    assert "<redacted>" in rec2.getMessage()


def test_parentheses_in_query_string_preserved_and_secrets_redacted() -> None:
    out1 = _scrubbed("/search?filter=(a)&token=REVIEW_PROBE")
    assert "REVIEW_PROBE" not in out1
    assert "?filter=(a)&token=<redacted>" in out1

    out2 = _scrubbed("/download?token=prefix(suffix)&state=REVIEW_PROBE")
    assert "prefix(suffix)" not in out2
    assert "REVIEW_PROBE" not in out2
    assert "?token=<redacted>&state=<redacted>" in out2




