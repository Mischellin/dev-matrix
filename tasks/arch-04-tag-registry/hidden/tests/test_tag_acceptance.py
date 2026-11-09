import pytest
from tags.service import RecipeTagService


def test_normalization_and_deduplication() -> None:
    svc = RecipeTagService()
    svc.save_recipe("r1", [" Dinner ", "dinner", "DINNER", "Pasta", ""])
    res = svc.get_recipe("r1")
    assert res is not None
    # Must be deduplicated and lowercase
    assert res["tags"] == ["dinner", "pasta"]


def test_alphabetical_ordering() -> None:
    svc = RecipeTagService()
    svc.save_recipe("r1", ["zucchini", "apple", "banana"])
    res = svc.get_recipe("r1")
    assert res is not None
    assert res["tags"] == ["apple", "banana", "zucchini"]


def test_list_recipes_filtering_case_insensitive() -> None:
    svc = RecipeTagService()
    svc.save_recipe("r1", ["quick", "dinner"])
    svc.save_recipe("r2", ["slow", "breakfast"])

    res_upper = svc.list_recipes(tag="DINNER")
    assert len(res_upper) == 1
    assert res_upper[0]["id"] == "r1"

    res_all = svc.list_recipes()
    assert len(res_all) == 2


def test_list_all_tags_sorted_and_cleaned() -> None:
    svc = RecipeTagService()
    svc.save_recipe("r1", ["soup", "dinner"])
    svc.save_recipe("r2", ["salad", "lunch"])

    tags = svc.list_all_tags()
    assert tags == ["dinner", "lunch", "salad", "soup"]


def test_delete_requires_explicit_delete_scope() -> None:
    svc = RecipeTagService()
    svc.save_recipe("r1", ["dessert"])

    # Attempt with only write scope must fail
    with pytest.raises(PermissionError, match="recipes:delete"):
        svc.delete_recipe("r1", scopes=["recipes:write", "recipes:read"])

    # Attempt with delete scope must succeed
    svc.delete_recipe("r1", scopes=["recipes:delete"])
    assert svc.get_recipe("r1") is None
    assert "dessert" not in svc.list_all_tags()
