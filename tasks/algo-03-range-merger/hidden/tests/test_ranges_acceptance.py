import pytest
from ranges import parse_ranges


def test_single_values_and_ranges() -> None:
    assert parse_ranges("1, 4-6, 9", 10) == [(1, 1), (4, 6), (9, 9)]


def test_sorts_and_merges_overlapping_or_adjacent_ranges() -> None:
    assert parse_ranges("8-9, 1-3, 3-5, 7", 10) == [(1, 5), (7, 9)]


def test_strips_whitespace() -> None:
    assert parse_ranges(" 2 - 4 , 8 ", 10) == [(2, 4), (8, 8)]


def test_nested_and_contained_intervals() -> None:
    assert parse_ranges("1-10, 3-7, 2-5", 20) == [(1, 10)]
    assert parse_ranges("1-20, 5", 20) == [(1, 20)]


def test_unsorted_disjoint_ranges_with_variable_spacing() -> None:
    assert parse_ranges("20-25, 1-5, 10-15", 30) == [(1, 5), (10, 15), (20, 25)]
    assert parse_ranges("  50-60  ,  10-20  ,  30-40  ", 100) == [(10, 20), (30, 40), (50, 60)]


def test_duplicate_ranges_and_shared_endpoints() -> None:
    assert parse_ranges("3-5, 3-5, 4-8, 1, 1", 10) == [(1, 1), (3, 8)]
    assert parse_ranges("1-5, 5-10", 15) == [(1, 10)]


def test_boundary_max_value_and_adjacent_chain() -> None:
    assert parse_ranges("95-100", 100) == [(95, 100)]
    assert parse_ranges("100", 100) == [(100, 100)]
    assert parse_ranges("1, 100", 100) == [(1, 1), (100, 100)]
    assert parse_ranges("1-2, 3-4, 5-6", 10) == [(1, 6)]


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
