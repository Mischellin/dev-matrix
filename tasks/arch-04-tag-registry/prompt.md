# Architecture & Data: Normalized Tag Registry with Scope Protection

## Context
In `src/tags/service.py`, implement an in-memory `RecipeTagService` that manages recipe tags and permissions.

## Requirements
1. **Tag Normalization & Deduplication:**
   - Tags are case-insensitive and trimmed of leading/trailing whitespace.
   - For example, `"Dinner"`, `"dinner "`, and `" dinner"` are stored as a single canonical tag: `"dinner"`.
   - Empty tags or whitespace-only tags must be silently ignored.
2. **Tag Set Replacement & Alphabetical Ordering:**
   - Calling `save_recipe(recipe_id: str, tags: list[str])` overwrites the existing tag set for that recipe.
   - Calling `get_recipe(recipe_id: str)` returns `{"id": recipe_id, "tags": [...]}` with tags sorted alphabetically in ascending order.
3. **Filtering & Cataloging:**
   - `list_recipes(tag: str | None = None) -> list[dict]` returns all recipes. If `tag` is provided, filters for recipes containing the tag (case-insensitively).
   - `list_all_tags() -> list[str]` returns all unique tags currently associated with any existing recipe, sorted alphabetically. If a recipe is deleted, its unreferenced tags must no longer appear in `list_all_tags()`.
4. **Security & Permission Separation:**
   - `delete_recipe(recipe_id: str, scopes: list[str]) -> None`:
     - Deleting a recipe requires the explicit scope `"recipes:delete"`.
     - If the caller only possesses `"recipes:write"` (or lacks `"recipes:delete"`), raise `PermissionError("Missing recipes:delete permission")`.
     - Upon deletion, the recipe is removed from the catalog.

## Definition of Done
All unit tests and acceptance tests pass, verifying normalization, alphabetical ordering, and permission checks.
