import pytest
from ranges import parse_ranges


def test_single_values_and_ranges() -> None:
    assert parse_ranges("1, 4-6, 9", 10) == [(1, 1), (4, 6), (9, 9)]


def test_sorts_and_merges_overlapping_or_adjacent_ranges() -> None:
    assert parse_ranges("8-9, 1-3, 3-5, 7", 10) == [(1, 5), (7, 9)]


def test_strips_whitespace() -> None:
    assert parse_ranges(" 2 - 4 , 8 ", 10) == [(2, 4), (8, 8)]


@pytest.mark.parametrize("value", ["", "   ", ",1", "1,", "1,,2"])
def test_rejects_empty_input_and_empty_terms(value: str) -> None:
    with pytest.raises(ValueError):
        parse_ranges(value, 10)


@pytest.mark.parametrize("value", ["a", "1-", "-2", "1-2-3", "1.5"])
def test_rejects_malformed_terms(value: str) -> None:
    with pytest.raises(ValueError):
        parse_ranges(value, 10)


@pytest.mark.parametrize("value", ["0", "-1", "4-2", "1-11"])
def test_rejects_nonpositive_reversed_and_out_of_bounds_values(value: str) -> None:
    with pytest.raises(ValueError):
        parse_ranges(value, 10)


@pytest.mark.parametrize(
    ("value", "limit"),
    [(None, 10), (1, 10), ("1", 0), ("1", -1), ("1", True)],
)
def test_rejects_invalid_argument_types_and_limits(value, limit) -> None:
    with pytest.raises(ValueError):
        parse_ranges(value, limit)
