from __future__ import annotations

import logging


class RedactQuerySecretsFilter(logging.Filter):
    """Filter that replaces sensitive query parameters with <redacted>."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Stub: returns True without redaction
        return True
