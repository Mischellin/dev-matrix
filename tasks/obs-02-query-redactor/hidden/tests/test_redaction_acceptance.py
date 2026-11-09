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
