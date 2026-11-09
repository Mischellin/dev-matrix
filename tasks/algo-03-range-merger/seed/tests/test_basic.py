import pytest
from ranges import parse_ranges


def test_signature_exists() -> None:
    with pytest.raises(NotImplementedError):
        parse_ranges("1-2", 10)
