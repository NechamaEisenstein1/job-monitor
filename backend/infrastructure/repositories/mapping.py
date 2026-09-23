"""Generic row <-> dataclass mapping (column names equal dataclass field names)."""
from dataclasses import fields
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


def to_domain(row: Any, cls: type[T], enums: dict[str, type[Enum]] | None = None) -> T:
    enums = enums or {}
    values = {}
    for f in fields(cls):  # type: ignore[arg-type]
        value = getattr(row, f.name)
        values[f.name] = enums[f.name](value) if f.name in enums and value is not None else value
    return cls(**values)


def to_values(obj: Any, exclude: tuple[str, ...] = ("id",)) -> dict[str, Any]:
    values = {}
    for f in fields(obj):
        if f.name in exclude:
            continue
        value = getattr(obj, f.name)
        values[f.name] = value.value if isinstance(value, Enum) else value
    return values
