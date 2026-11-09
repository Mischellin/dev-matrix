from __future__ import annotations


def _normalize_tag(tag: str) -> str:
    return tag.strip().lower()


class RecipeTagService:
    def __init__(self) -> None:
        self._recipes: dict[str, set[str]] = {}

    def save_recipe(self, recipe_id: str, tags: list[str]) -> None:
        clean_tags = set()
        for t in tags:
            norm = _normalize_tag(t)
            if norm:
                clean_tags.add(norm)
        self._recipes[recipe_id] = clean_tags

    def get_recipe(self, recipe_id: str) -> dict | None:
        if recipe_id not in self._recipes:
            return None
        return {"id": recipe_id, "tags": sorted(self._recipes[recipe_id])}

    def list_recipes(self, tag: str | None = None) -> list[dict]:
        out = []
        target = _normalize_tag(tag) if tag else None
        for rid, tags in self._recipes.items():
            if target is None or target in tags:
                out.append({"id": rid, "tags": sorted(tags)})
        return out

    def list_all_tags(self) -> list[str]:
        all_t = set()
        for tags in self._recipes.values():
            all_t.update(tags)
        return sorted(all_t)

    def delete_recipe(self, recipe_id: str, scopes: list[str]) -> None:
        if "recipes:delete" not in scopes:
            raise PermissionError("Missing recipes:delete permission")
        self._recipes.pop(recipe_id, None)
