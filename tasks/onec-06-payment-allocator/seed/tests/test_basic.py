from __future__ import annotations

from pathlib import Path

from onec.bsl_engine import BSLRuntime


def test_basic_single_order_exact_match() -> None:
    runtime = BSLRuntime()
    module = runtime.load_module(
        Path(__file__).parent.parent / "src" / "onec" / "РазнесениеПлатежей.bsl"
    )

    params = runtime.new_structure(
        СуммаПлатежа=5000.0,
        Контрагент="ООО Тест",
        Договор="Д-1",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )
    r = orders.Добавить()
    r.НомерЗаказа = "ЗК-101"
    r.ДатаЗаказа = "2026-11-01"
    r.СуммаЗаказа = 5000.0
    r.ОплаченоРанее = 0.0
    r.СтавкаНДС = "Без НДС"

    res = module.РазнестиОплатуПоЗаказам(params, orders)
    assert res.ВсегоРаспределено == 5000.0
    assert res.ТаблицаРаспределения.Количество() == 1
    row = res.ТаблицаРаспределения[0]
    assert row.НомерЗаказа == "ЗК-101"
    assert row.СуммаОплаты == 5000.0
    assert row.ДолгПослеОплаты == 0.0


def test_basic_two_orders_already_sorted() -> None:
    runtime = BSLRuntime()
    module = runtime.load_module(
        Path(__file__).parent.parent / "src" / "onec" / "РазнесениеПлатежей.bsl"
    )

    params = runtime.new_structure(
        СуммаПлатежа=3000.0,
        Контрагент="ООО Клиент",
        Договор="Д-2",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )
    r1 = orders.Добавить()
    r1.НомерЗаказа = "ЗК-101"
    r1.ДатаЗаказа = "2026-11-01"
    r1.СуммаЗаказа = 2000.0
    r1.ОплаченоРанее = 0.0
    r1.СтавкаНДС = "Без НДС"

    r2 = orders.Добавить()
    r2.НомерЗаказа = "ЗК-102"
    r2.ДатаЗаказа = "2026-11-02"
    r2.СуммаЗаказа = 2000.0
    r2.ОплаченоРанее = 0.0
    r2.СтавкаНДС = "Без НДС"

    res = module.РазнестиОплатуПоЗаказам(params, orders)
    assert res.ВсегоРаспределено == 3000.0
    assert res.ТаблицаРаспределения.Количество() == 2
    assert res.ТаблицаРаспределения[0].СуммаОплаты == 2000.0
    assert res.ТаблицаРаспределения[1].СуммаОплаты == 1000.0
    assert res.ТаблицаРаспределения[1].ДолгПослеОплаты == 1000.0


def test_basic_structure_and_column_names() -> None:
    runtime = BSLRuntime()
    module = runtime.load_module(
        Path(__file__).parent.parent / "src" / "onec" / "РазнесениеПлатежей.bsl"
    )

    params = runtime.new_structure(
        СуммаПлатежа=100.0,
        Контрагент="ООО Тест",
        Договор="Д-1",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )
    res = module.РазнестиОплатуПоЗаказам(params, orders)
    cols = res.ТаблицаРаспределения.Колонки._list
    assert "НомерЗаказа" in cols
    assert "СуммаОплаты" in cols
    assert "СуммаНДС" in cols
    assert "ДолгПослеОплаты" in cols
