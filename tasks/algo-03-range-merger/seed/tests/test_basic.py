from ranges import parse_ranges


def test_signature_exists() -> None:
    assert callable(parse_ranges)
