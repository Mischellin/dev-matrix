from __future__ import annotations

from pathlib import Path

import pytest
from onec.bsl_engine import BSLRuntime, BSLRuntimeError


@pytest.fixture
def bsl_module():
    runtime = BSLRuntime()
    mod_path = Path.cwd() / "src" / "onec" / "РазнесениеПлатежей.bsl"
    return runtime, runtime.load_module(mod_path)


def test_reject_negative_payment_sum(bsl_module) -> None:
    runtime, module = bsl_module
    params = runtime.new_structure(
        СуммаПлатежа=-100.0,
        Контрагент="ООО Тест",
        Договор="Д-1",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )
    with pytest.raises(BSLRuntimeError, match="Отрицательная сумма|недопустима"):
        module.РазнестиОплатуПоЗаказам(params, orders)


def test_zero_payment_returns_empty_and_zero_totals(bsl_module) -> None:
    runtime, module = bsl_module
    params = runtime.new_structure(
        СуммаПлатежа=0.0,
        Контрагент="ООО Тест",
        Договор="Д-1",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )
    r = orders.Добавить()
    r.НомерЗаказа = "ЗК-01"
    r.ДатаЗаказа = "2026-11-01"
    r.СуммаЗаказа = 1000.0
    r.ОплаченоРанее = 0.0
    r.СтавкаНДС = "20%"

    res = module.РазнестиОплатуПоЗаказам(params, orders)
    assert res.ВсегоРаспределено == 0.0
    assert res.ОстатокАванса == 0.0
    assert res.ВсегоНДС == 0.0
    assert res.ТаблицаРаспределения.Количество() == 0


def test_empty_orders_table_returns_full_advance(bsl_module) -> None:
    runtime, module = bsl_module
    params = runtime.new_structure(
        СуммаПлатежа=7500.0,
        Контрагент="ООО Тест",
        Договор="Д-1",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )
    res = module.РазнестиОплатуПоЗаказам(params, orders)
    assert res.ВсегоРаспределено == 0.0
    assert res.ОстатокАванса == 7500.0
    assert res.ВсегоНДС == 0.0
    assert res.ТаблицаРаспределения.Количество() == 0


def test_fifo_sort_by_date(bsl_module) -> None:
    runtime, module = bsl_module
    params = runtime.new_structure(
        СуммаПлатежа=5000.0,
        Контрагент="ООО Клиент",
        Договор="Д-1",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )

    # Newer order added first in input
    r2 = orders.Добавить()
    r2.НомерЗаказа = "ЗК-NEW"
    r2.ДатаЗаказа = "2026-11-05"
    r2.СуммаЗаказа = 5000.0
    r2.ОплаченоРанее = 0.0
    r2.СтавкаНДС = "Без НДС"

    # Older order added second
    r1 = orders.Добавить()
    r1.НомерЗаказа = "ЗК-OLD"
    r1.ДатаЗаказа = "2026-10-25"
    r1.СуммаЗаказа = 5000.0
    r1.ОплаченоРанее = 0.0
    r1.СтавкаНДС = "Без НДС"

    res = module.РазнестиОплатуПоЗаказам(params, orders)
    assert res.ТаблицаРаспределения.Количество() == 1
    # Must allocate to the older order first!
    assert res.ТаблицаРаспределения[0].НомерЗаказа == "ЗК-OLD"
    assert res.ТаблицаРаспределения[0].СуммаОплаты == 5000.0


def test_fifo_tie_break_by_order_number(bsl_module) -> None:
    runtime, module = bsl_module
    params = runtime.new_structure(
        СуммаПлатежа=2000.0,
        Контрагент="ООО Клиент",
        Договор="Д-1",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )

    r2 = orders.Добавить()
    r2.НомерЗаказа = "ЗК-002"
    r2.ДатаЗаказа = "2026-11-01"
    r2.СуммаЗаказа = 2000.0
    r2.ОплаченоРанее = 0.0
    r2.СтавкаНДС = "Без НДС"

    r1 = orders.Добавить()
    r1.НомерЗаказа = "ЗК-001"
    r1.ДатаЗаказа = "2026-11-01"
    r1.СуммаЗаказа = 2000.0
    r1.ОплаченоРанее = 0.0
    r1.СтавкаНДС = "Без НДС"

    res = module.РазнестиОплатуПоЗаказам(params, orders)
    assert res.ТаблицаРаспределения.Количество() == 1
    # When dates are equal, smaller order number gets priority
    assert res.ТаблицаРаспределения[0].НомерЗаказа == "ЗК-001"


def test_advance_balance_on_overpayment(bsl_module) -> None:
    runtime, module = bsl_module
    params = runtime.new_structure(
        СуммаПлатежа=10000.0,
        Контрагент="ООО Клиент",
        Договор="Д-1",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )

    r = orders.Добавить()
    r.НомерЗаказа = "ЗК-01"
    r.ДатаЗаказа = "2026-11-01"
    r.СуммаЗаказа = 6000.0
    r.ОплаченоРанее = 0.0
    r.СтавкаНДС = "Без НДС"

    res = module.РазнестиОплатуПоЗаказам(params, orders)
    assert res.ВсегоРаспределено == 6000.0
    assert res.ОстатокАванса == 4000.0
    assert res.ТаблицаРаспределения[0].ДолгПослеОплаты == 0.0


def test_partial_allocation_across_orders(bsl_module) -> None:
    runtime, module = bsl_module
    params = runtime.new_structure(
        СуммаПлатежа=7500.0,
        Контрагент="ООО Клиент",
        Договор="Д-1",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )

    r1 = orders.Добавить()
    r1.НомерЗаказа = "ЗК-01"
    r1.ДатаЗаказа = "2026-11-01"
    r1.СуммаЗаказа = 5000.0
    r1.ОплаченоРанее = 0.0
    r1.СтавкаНДС = "Без НДС"

    r2 = orders.Добавить()
    r2.НомерЗаказа = "ЗК-02"
    r2.ДатаЗаказа = "2026-11-02"
    r2.СуммаЗаказа = 5000.0
    r2.ОплаченоРанее = 0.0
    r2.СтавкаНДС = "Без НДС"

    res = module.РазнестиОплатуПоЗаказам(params, orders)
    assert res.ВсегоРаспределено == 7500.0
    assert res.ОстатокАванса == 0.0
    assert res.ТаблицаРаспределения.Количество() == 2
    assert res.ТаблицаРаспределения[0].СуммаОплаты == 5000.0
    assert res.ТаблицаРаспределения[0].ДолгПослеОплаты == 0.0
    assert res.ТаблицаРаспределения[1].СуммаОплаты == 2500.0
    assert res.ТаблицаРаспределения[1].ДолгПослеОплаты == 2500.0


def test_vat_20_percent_calculation_and_rounding(bsl_module) -> None:
    runtime, module = bsl_module
    params = runtime.new_structure(
        СуммаПлатежа=1000.0,
        Контрагент="ООО Партнер",
        Договор="Д-НДС",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )
    r = orders.Добавить()
    r.НомерЗаказа = "ЗК-НДС20"
    r.ДатаЗаказа = "2026-11-01"
    r.СуммаЗаказа = 1000.0
    r.ОплаченоРанее = 0.0
    r.СтавкаНДС = "20%"

    res = module.РазнестиОплатуПоЗаказам(params, orders)
    # 1000 * 20 / 120 = 166.6666... -> 166.67
    assert res.ТаблицаРаспределения[0].СуммаНДС == 166.67
    assert res.ВсегоНДС == 166.67


def test_vat_10_percent_calculation_and_rounding(bsl_module) -> None:
    runtime, module = bsl_module
    params = runtime.new_structure(
        СуммаПлатежа=1100.0,
        Контрагент="ООО Партнер",
        Договор="Д-НДС",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )
    r = orders.Добавить()
    r.НомерЗаказа = "ЗК-НДС10"
    r.ДатаЗаказа = "2026-11-01"
    r.СуммаЗаказа = 1100.0
    r.ОплаченоРанее = 0.0
    r.СтавкаНДС = "10%"

    res = module.РазнестиОплатуПоЗаказам(params, orders)
    # 1100 * 10 / 110 = 100.00
    assert res.ТаблицаРаспределения[0].СуммаНДС == 100.0
    assert res.ВсегоНДС == 100.0


def test_mixed_vat_rates_and_total_vat(bsl_module) -> None:
    runtime, module = bsl_module
    params = runtime.new_structure(
        СуммаПлатежа=6000.0,
        Контрагент="ООО Смешанный",
        Договор="Д-МИКС",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )

    # 1st order: 2000 @ 20% -> 2000 * 20 / 120 = 333.33
    r1 = orders.Добавить()
    r1.НомерЗаказа = "ЗК-01"
    r1.ДатаЗаказа = "2026-11-01"
    r1.СуммаЗаказа = 2000.0
    r1.ОплаченоРанее = 0.0
    r1.СтавкаНДС = "20%"

    # 2nd order: 2000 @ 10% -> 2000 * 10 / 110 = 181.82
    r2 = orders.Добавить()
    r2.НомерЗаказа = "ЗК-02"
    r2.ДатаЗаказа = "2026-11-02"
    r2.СуммаЗаказа = 2000.0
    r2.ОплаченоРанее = 0.0
    r2.СтавкаНДС = "10%"

    # 3rd order: 2000 @ Без НДС -> 0.0
    r3 = orders.Добавить()
    r3.НомерЗаказа = "ЗК-03"
    r3.ДатаЗаказа = "2026-11-03"
    r3.СуммаЗаказа = 2000.0
    r3.ОплаченоРанее = 0.0
    r3.СтавкаНДС = "Без НДС"

    res = module.РазнестиОплатуПоЗаказам(params, orders)
    assert res.ВсегоРаспределено == 6000.0
    # 333.33 + 181.82 = 515.15
    assert res.ВсегоНДС == 515.15


def test_skip_already_fully_paid_orders(bsl_module) -> None:
    runtime, module = bsl_module
    params = runtime.new_structure(
        СуммаПлатежа=3000.0,
        Контрагент="ООО Тест",
        Договор="Д-1",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )

    # Order 1: fully paid previously (5000 - 5000 = 0)
    r1 = orders.Добавить()
    r1.НомерЗаказа = "ЗК-CLOSED"
    r1.ДатаЗаказа = "2026-11-01"
    r1.СуммаЗаказа = 5000.0
    r1.ОплаченоРанее = 5000.0
    r1.СтавкаНДС = "20%"

    # Order 2: open
    r2 = orders.Добавить()
    r2.НомерЗаказа = "ЗК-OPEN"
    r2.ДатаЗаказа = "2026-11-02"
    r2.СуммаЗаказа = 3000.0
    r2.ОплаченоРанее = 0.0
    r2.СтавкаНДС = "Без НДС"

    res = module.РазнестиОплатуПоЗаказам(params, orders)
    assert res.ТаблицаРаспределения.Количество() == 1
    assert res.ТаблицаРаспределения[0].НомерЗаказа == "ЗК-OPEN"
    assert res.ТаблицаРаспределения[0].СуммаОплаты == 3000.0


def test_order_with_prior_partial_payment(bsl_module) -> None:
    runtime, module = bsl_module
    params = runtime.new_structure(
        СуммаПлатежа=5000.0,
        Контрагент="ООО Тест",
        Договор="Д-1",
        ДатаПлатежа="2026-11-10",
    )
    orders = runtime.new_value_table(
        ["НомерЗаказа", "ДатаЗаказа", "СуммаЗаказа", "ОплаченоРанее", "СтавкаНДС"]
    )

    # Order: 10000 total, 8000 already paid, remaining debt is 2000
    r = orders.Добавить()
    r.НомерЗаказа = "ЗК-PARTIAL"
    r.ДатаЗаказа = "2026-11-01"
    r.СуммаЗаказа = 10000.0
    r.ОплаченоРанее = 8000.0
    r.СтавкаНДС = "Без НДС"

    res = module.РазнестиОплатуПоЗаказам(params, orders)
    assert res.ВсегоРаспределено == 2000.0
    assert res.ОстатокАванса == 3000.0
    assert res.ТаблицаРаспределения[0].СуммаОплаты == 2000.0
    assert res.ТаблицаРаспределения[0].ДолгПослеОплаты == 0.0
