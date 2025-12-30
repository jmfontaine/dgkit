"""Data filters for transforming or dropping records."""

from typing import Any, NamedTuple, Protocol


class Filter(Protocol):
    """Protocol for record filters."""

    def __call__(self, record: NamedTuple) -> NamedTuple | None:
        """Return modified record, or None to drop it."""
        ...


class DropByValue:
    """Drop records where a field matches (or doesn't match) a value."""

    def __init__(self, field: str, value: Any, negate: bool = False):
        self.field = field
        self.value = value
        self.negate = negate

    def __call__(self, record: NamedTuple) -> NamedTuple | None:
        record_value = getattr(record, self.field, None)
        # Convert to string for comparison since CLI values are strings
        matches = str(record_value) == str(self.value)
        if self.negate:
            matches = not matches
        if matches:
            return None
        return record


class UnsetFields:
    """Set specified fields to None."""

    def __init__(self, fields: list[str]):
        self.fields = set(fields)

    def __call__(self, record: NamedTuple) -> NamedTuple | None:
        if not self.fields:
            return record
        updates = {f: None for f in self.fields if hasattr(record, f)}
        return record._replace(**updates) if updates else record


class FilterChain:
    """Compose multiple filters into a single filter."""

    def __init__(self, filters: list[Filter]):
        self.filters = filters

    def __call__(self, record: NamedTuple) -> NamedTuple | None:
        for f in self.filters:
            record = f(record)
            if record is None:
                return None
        return record


def parse_drop_if(values: list[str]) -> list[DropByValue]:
    """Parse --drop-if field=value or field!=value arguments into DropByValue filters."""
    filters = []
    for value in values:
        if "!=" in value:
            field, val = value.split("!=", 1)
            filters.append(DropByValue(field.strip(), val.strip(), negate=True))
        elif "=" in value:
            field, val = value.split("=", 1)
            filters.append(DropByValue(field.strip(), val.strip(), negate=False))
        else:
            raise ValueError(f"Invalid --drop-if format: {value!r} (expected field=value or field!=value)")
    return filters


def parse_unset(values: list[str]) -> UnsetFields | None:
    """Parse --unset field1,field2 arguments into UnsetFields filter."""
    fields = []
    for value in values:
        fields.extend(f.strip() for f in value.split(",") if f.strip())
    return UnsetFields(fields) if fields else None
