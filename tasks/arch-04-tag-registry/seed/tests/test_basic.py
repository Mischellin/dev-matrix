from tags.service import RecipeTagService


def test_basic_save_and_retrieve() -> None:
    svc = RecipeTagService()
    svc.save_recipe("r1", ["pasta", "italian"])
    res = svc.get_recipe("r1")
    assert res is not None
    assert "pasta" in res["tags"]
