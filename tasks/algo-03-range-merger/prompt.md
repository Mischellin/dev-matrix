# Algorithm Task: Interval String Parser and Overlap Merger

## Context
Implement `parse_ranges(text: str, max_value: int) -> list[tuple[int, int]]` in `src/ranges/ranges.py`.

## Requirements
1. **Input format:**
   - Comma-separated list of individual integers and inclusive ranges, e.g. `"1, 4-6, 9"`.
   - Whitespace around items and hyphens must be allowed (e.g. `" 2 - 4 , 8 "`).
2. **Output:**
   - Sorted list of inclusive integer pairs `(start, end)`.
   - Overlapping and directly adjacent intervals must be merged into continuous ranges (e.g. `"8-9, 1-3, 3-5, 7"` becomes `[(1, 5), (7, 9)]`).
3. **Error Handling (`ValueError`):**
   - Must raise `ValueError` on empty input or whitespace-only input (`""`, `"   "`).
   - Must raise `ValueError` on empty items (e.g. `",1"`, `"1,"`, `"1,,2"`).
   - Must raise `ValueError` on malformed items (e.g. `"a"`, `"1-"`, `"-2"`, `"1-2-3"`, `"1.5"`).
   - Must raise `ValueError` on non-positive integers ($\le 0$), reversed ranges (e.g. `"4-2"`), or values exceeding `max_value`.
   - Must raise `ValueError` on invalid types (e.g. `text` not a string, `max_value` not a positive integer, or booleans).

## Definition of Done
All unit tests and edge cases pass with strict `ValueError` validations.
