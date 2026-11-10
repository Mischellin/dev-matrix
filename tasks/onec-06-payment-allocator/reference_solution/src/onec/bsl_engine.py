"""1C:Enterprise (BSL) Runtime and Execution Engine for Automated Benchmark Testing."""

from __future__ import annotations

import re
from collections.abc import Iterator
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any


class BSLSyntaxError(Exception):
    """Raised when BSL module contains invalid syntax or violates 1C standards."""


class BSLRuntimeError(Exception):
    """Raised when 1C runtime exception occurs (e.g. ВызватьИсключение)."""


def Окр(val: Any, precision: int = 0) -> int | float:
    """1C Окр() implementation with standard 1C ROUND_HALF_UP mode."""
    d = Decimal(str(val))
    if precision == 0:
        return int(d.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    fmt = "0." + "0" * precision
    return float(d.quantize(Decimal(fmt), rounding=ROUND_HALF_UP))


def Цел(val: Any) -> int:
    return int(val)


def Строка(val: Any) -> str:
    return str(val)


def Число(val: Any) -> float:
    return float(val)


Мин = min
Макс = max


class Структура:
    """1C:Enterprise Структура (Key-Value structure with attribute and index access)."""

    def __init__(self, **kwargs: Any) -> None:
        self._data: dict[str, Any] = dict(kwargs)

    def Вставить(self, key: str, val: Any) -> None:
        self._data[key] = val

    def Свойство(self, key: str) -> bool:
        return key in self._data

    def Количество(self) -> int:
        return len(self._data)

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"Структура 1С не содержит свойства '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_data":
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __repr__(self) -> str:
        return f"Структура({self._data!r})"


class СтрокаТаблицыЗначений:
    """Row in a 1C ТаблицаЗначений."""

    def __init__(self, columns: list[str]) -> None:
        self._cols = set(columns)
        self._data: dict[str, Any] = {c: None for c in columns}

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"Колонка '{name}' не найдена в строке таблицы значений")

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("_cols", "_data"):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def __getitem__(self, item: str) -> Any:
        return self._data[item]

    def __setitem__(self, item: str, value: Any) -> None:
        self._data[item] = value

    def __repr__(self) -> str:
        return f"СтрокаТаблицы({self._data!r})"


class КолонкиТаблицы:
    def __init__(self) -> None:
        self._list: list[str] = []

    def Добавить(self, name: str) -> str:
        if name not in self._list:
            self._list.append(name)
        return name

    def Количество(self) -> int:
        return len(self._list)


class ТаблицаЗначений:
    """1C:Enterprise ТаблицаЗначений (ValueTable)."""

    def __init__(self) -> None:
        self.Колонки = КолонкиТаблицы()
        self._rows: list[СтрокаТаблицыЗначений] = []

    def Добавить(self) -> СтрокаТаблицыЗначений:
        row = СтрокаТаблицыЗначений(self.Колонки._list)
        self._rows.append(row)
        return row

    def Количество(self) -> int:
        return len(self._rows)

    def __iter__(self) -> Iterator[СтрокаТаблицыЗначений]:
        return iter(self._rows)

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, idx: int) -> СтрокаТаблицыЗначений:
        return self._rows[idx]

    def Сортировать(self, columns_spec: str) -> None:
        """Sort rows according to 1C sort specification (e.g. 'ДатаЗаказа Возр, НомерЗаказа Убыв')."""
        specs = [s.strip().split() for s in columns_spec.split(",") if s.strip()]
        for spec in reversed(specs):
            col = spec[0]
            desc = len(spec) > 1 and spec[1].lower().startswith("убыв")
            self._rows.sort(
                key=lambda r: (getattr(r, col) is None, getattr(r, col)),
                reverse=desc,
            )

    def __repr__(self) -> str:
        return f"ТаблицаЗначений(колонки={self.Колонки._list}, строк={len(self._rows)})"


class Массив:
    """1C:Enterprise Массив."""

    def __init__(self, *items: Any) -> None:
        self._items: list[Any] = list(items)

    def Добавить(self, item: Any) -> None:
        self._items.append(item)

    def Количество(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, idx: int) -> Any:
        return self._items[idx]


class BSLModule:
    """Represents an executed BSL module."""

    def __init__(self, namespace: dict[str, Any]) -> None:
        self._ns = namespace

    def __getattr__(self, name: str) -> Any:
        if name in self._ns:
            return self._ns[name]
        raise AttributeError(f"Модуль 1С не экспортирует процедуру/функцию '{name}'")


class BSLRuntime:
    """Loads, validates, and executes 1C:Enterprise (BSL) files."""

    FORBIDDEN_PYTHON_TOKENS = (
        r"\bimport\s+",
        r"\bfrom\s+\w+\s+import",
        r"\bdef\s+",
        r"\bclass\s+",
        r"\blambda\s+",
        r"\b__\w+__\b",
    )

    def validate_bsl_syntax(self, source: str) -> None:
        # Reject Python-specific syntax
        for pat in self.FORBIDDEN_PYTHON_TOKENS:
            if re.search(pat, source):
                raise BSLSyntaxError(
                    "Файл содержит запрещенные конструкции Python. Модуль должен быть написан на языке 1С (BSL)."
                )

        # Check required BSL keywords
        if not re.search(r"(?i)\b(?:Функция|Процедура)\b", source):
            raise BSLSyntaxError("Модуль 1С должен содержать определение процедуры или функции.")

        # Check balanced blocks
        fn_count = len(re.findall(r"(?i)\b(?:Функция|Процедура)\b", source))
        end_fn_count = len(re.findall(r"(?i)\b(?:КонецФункции|КонецПроцедуры)\b", source))
        if fn_count != end_fn_count:
            raise BSLSyntaxError(
                f"Не сбалансированы функции/процедуры: объявлено {fn_count}, закрыто {end_fn_count}"
            )

        if_count = len(re.findall(r"(?i)\bЕсли\b", source))
        end_if_count = len(re.findall(r"(?i)\bКонецЕсли\b", source))
        if if_count != end_if_count:
            raise BSLSyntaxError(
                f"Не сбалансированы условия: Если={if_count}, КонецЕсли={end_if_count}"
            )

        loop_count = len(re.findall(r"(?i)\b(?:Для|Пока)\b", source))
        end_loop_count = len(re.findall(r"(?i)\bКонецЦикла\b", source))
        if loop_count != end_loop_count:
            raise BSLSyntaxError(
                f"Не сбалансированы циклы: объявлено {loop_count}, закрыто {end_loop_count}"
            )

    def transpile(self, source: str) -> str:
        self.validate_bsl_syntax(source)
        lines = source.splitlines()
        py_lines: list[str] = []
        indent = 0

        for line in lines:
            raw = line.strip()
            if "//" in raw:
                raw = raw.split("//")[0].strip()
            if not raw:
                continue

            if raw.endswith(";"):
                raw = raw[:-1].strip()

            # Block closings
            if re.match(r"(?i)^(КонецФункции|КонецПроцедуры|КонецЕсли|КонецЦикла)", raw):
                indent = max(0, indent - 1)
                continue
            elif re.match(r"(?i)^ИначеЕсли\b", raw):
                indent = max(0, indent - 1)
                m = re.match(r"(?i)^ИначеЕсли\s+(.+?)\s+Тогда", raw)
                cond = m.group(1) if m else "True"
                cond = self._convert_condition(cond)
                py_lines.append("    " * indent + f"elif {cond}:")
                indent += 1
                continue
            elif re.match(r"(?i)^Иначе\b", raw):
                indent = max(0, indent - 1)
                py_lines.append("    " * indent + "else:")
                indent += 1
                continue

            prefix = "    " * indent

            # Function / Procedure declaration
            m_fn = re.match(
                r"(?i)^(?:Функция|Процедура)\s+([a-zA-Zа-яА-Я0-9_]+)\s*\((.*?)\)(?:\s+Экспорт)?",
                raw,
            )
            if m_fn:
                name, params = m_fn.group(1), m_fn.group(2)
                py_lines.append(f"{prefix}def {name}({params}):")
                indent += 1
                continue

            # If statement
            m_if = re.match(r"(?i)^Если\s+(.+?)\s+Тогда", raw)
            if m_if:
                cond = self._convert_condition(m_if.group(1))
                py_lines.append(f"{prefix}if {cond}:")
                indent += 1
                continue

            # For Each loop
            m_for = re.match(r"(?i)^Для\s+Каждого\s+([a-zA-Zа-яА-Я0-9_]+)\s+Из\s+(.+?)\s+Цикл", raw)
            if m_for:
                var, iterable = m_for.group(1), m_for.group(2)
                py_lines.append(f"{prefix}for {var} in {iterable}:")
                indent += 1
                continue

            # Break
            if re.match(r"(?i)^Прервать", raw):
                py_lines.append(f"{prefix}break")
                continue

            # Continue
            if re.match(r"(?i)^Продолжить", raw):
                py_lines.append(f"{prefix}continue")
                continue

            # Return
            m_ret = re.match(r"(?i)^Возврат(?:\s+(.+))?", raw)
            if m_ret:
                expr = m_ret.group(1) or "None"
                py_lines.append(f"{prefix}return {expr}")
                continue

            # Exception
            m_exc = re.match(r"(?i)^ВызватьИсключение(?:\s+(.+))?", raw)
            if m_exc:
                expr = m_exc.group(1) or '"Ошибка выполнения 1С"'
                py_lines.append(f"{prefix}raise BSLRuntimeError({expr})")
                continue

            # Replacements for instantiation
            stmt = re.sub(r"(?i)\bНовый\s+Структура\b", "Структура()", raw)
            stmt = re.sub(r"(?i)\bНовый\s+ТаблицаЗначений\b", "ТаблицаЗначений()", stmt)
            stmt = re.sub(r"(?i)\bНовый\s+Массив\b", "Массив()", stmt)

            py_lines.append(f"{prefix}{stmt}")

        return "\n".join(py_lines)

    def _convert_condition(self, cond: str) -> str:
        cond = cond.replace("<>", "!=")
        cond = re.sub(r"(?<![<>=!])=(?![=])", "==", cond)
        cond = re.sub(r"(?i)\bИли\b", " or ", cond)
        cond = re.sub(r"(?i)\bИ\b", " and ", cond)
        cond = re.sub(r"(?i)\bНе\b", " not ", cond)
        cond = re.sub(r"(?i)\bИстина\b", "True", cond)
        cond = re.sub(r"(?i)\bЛожь\b", "False", cond)
        cond = re.sub(r"(?i)\bНеопределено\b", "None", cond)
        return cond

    def load_module(self, path: Path | str) -> BSLModule:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"1C module not found: {path}")

        source = p.read_text(encoding="utf-8")
        py_code = self.transpile(source)

        namespace: dict[str, Any] = {
            "Структура": Структура,
            "ТаблицаЗначений": ТаблицаЗначений,
            "Массив": Массив,
            "BSLRuntimeError": BSLRuntimeError,
            "Окр": Окр,
            "Мин": Мин,
            "Макс": Макс,
            "Цел": Цел,
            "Строка": Строка,
            "Число": Число,
        }

        exec(compile(py_code, str(p), "exec"), namespace)  # noqa: S102
        return BSLModule(namespace)

    def new_structure(self, **kwargs: Any) -> Структура:
        return Структура(**kwargs)

    def new_value_table(self, columns: list[str]) -> ТаблицаЗначений:
        tv = ТаблицаЗначений()
        for c in columns:
            tv.Колонки.Добавить(c)
        return tv

    def new_array(self, *items: Any) -> Массив:
        return Массив(*items)
