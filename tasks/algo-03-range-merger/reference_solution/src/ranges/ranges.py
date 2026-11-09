from __future__ import annotations


def parse_ranges(text: str, max_value: int) -> list[tuple[int, int]]:
    """Parse comma-separated intervals and merge overlapping/adjacent bounds."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if isinstance(max_value, bool) or not isinstance(max_value, int) or max_value < 1:
        raise ValueError("max_value must be a positive integer")
    if not text.strip():
        raise ValueError("text cannot be empty")

    parts = text.split(",")
    raw_intervals = []
    for part in parts:
        trimmed = part.strip()
        if not trimmed:
            raise ValueError("empty term")
        if "-" in trimmed:
            sub = trimmed.split("-")
            if len(sub) != 2:
                raise ValueError(f"malformed range: {trimmed}")
            left_s, right_s = sub[0].strip(), sub[1].strip()
            if not left_s or not right_s or not left_s.isdigit() or not right_s.isdigit():
                raise ValueError(f"malformed range boundaries: {trimmed}")
            start, end = int(left_s), int(right_s)
        else:
            if not trimmed.isdigit():
                raise ValueError(f"malformed integer: {trimmed}")
            start = end = int(trimmed)

        if start < 1 or end < 1 or start > end or end > max_value:
            raise ValueError(f"out of bounds: ({start}, {end}) for max {max_value}")

        raw_intervals.append((start, end))

    raw_intervals.sort(key=lambda x: x[0])
    merged: list[tuple[int, int]] = []
    for s, e in raw_intervals:
        if not merged:
            merged.append((s, e))
        else:
            last_s, last_e = merged[-1]
            if s <= last_e + 1:
                merged[-1] = (last_s, max(last_e, e))
            else:
                merged.append((s, e))

    return merged
