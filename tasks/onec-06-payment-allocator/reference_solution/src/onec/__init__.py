"""1C BSL evaluation package."""

from .bsl_engine import (
    BSLModule,
    BSLRuntime,
    BSLRuntimeError,
    BSLSyntaxError,
    Массив,
    Структура,
    ТаблицаЗначений,
)

__all__ = [
    "BSLModule",
    "BSLRuntime",
    "BSLRuntimeError",
    "BSLSyntaxError",
    "Массив",
    "Структура",
    "ТаблицаЗначений",
]
