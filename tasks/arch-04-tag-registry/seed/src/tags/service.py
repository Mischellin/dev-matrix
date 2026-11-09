from __future__ import annotations


class RecipeTagService:
    def __init__(self) -> None:
        self._recipes: dict[str, list[str]] = {}

    def save_recipe(self, recipe_id: str, tags: list[str]) -> None:
        # Naive: stores tags as is, without case normalization
        self._recipes[recipe_id] = list(tags)

    def get_recipe(self, recipe_id: str) -> dict | None:
        if recipe_id not in self._recipes:
            return None
        return {"id": recipe_id, "tags": self._recipes[recipe_id]}

    def list_recipes(self, tag: str | None = None) -> list[dict]:
        out = []
        for rid, tags in self._recipes.items():
            if tag is None or tag in tags:
                out.append({"id": rid, "tags": tags})
        return out

    def list_all_tags(self) -> list[str]:
        all_t = set()
        for tags in self._recipes.values():
            all_t.update(tags)
        return list(all_t)

    def delete_recipe(self, recipe_id: str, scopes: list[str]) -> None:
        # Flaw: permits deletion if recipes:write is present
        if "recipes:write" not in scopes and "recipes:delete" not in scopes:
            raise PermissionError("Access denied")
        self._recipes.pop(recipe_id, None)
