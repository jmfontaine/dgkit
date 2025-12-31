"""Data filters for transforming or dropping records.

Filter expression grammar (BNF):
    expression  ::= or_expr
    or_expr     ::= and_expr (OR and_expr)*
    and_expr    ::= atom (AND atom)*
    atom        ::= comparison | '(' expression ')'
    comparison  ::= field operator value
    field       ::= identifier ('.' identifier)*
    operator    ::= '==' | '!=' | '>' | '>=' | '<' | '<='
    value       ::= string | number | 'true' | 'false' | 'null'
"""

from typing import Any, NamedTuple, Protocol

import pyparsing as pp

# Enable packrat parsing for recursive grammar performance
pp.ParserElement.enable_packrat()


class Filter(Protocol):
    """Protocol for record filters."""

    def __call__(self, record: NamedTuple) -> NamedTuple | None:
        """Return modified record, or None to drop it."""
        ...


# --- Expression Parser ---

def _build_parser() -> pp.ParserElement:
    """Build the filter expression parser."""
    # Operators
    EQ = pp.Literal("==").set_name("==")
    NE = pp.Literal("!=").set_name("!=")
    GE = pp.Literal(">=").set_name(">=")
    LE = pp.Literal("<=").set_name("<=")
    GT = pp.Literal(">").set_name(">")
    LT = pp.Literal("<").set_name("<")
    comparison_op = (EQ | NE | GE | LE | GT | LT).set_name("operator")

    # Keywords (case-insensitive)
    AND = pp.CaselessKeyword("and")
    OR = pp.CaselessKeyword("or")
    TRUE = pp.CaselessKeyword("true").set_parse_action(pp.replace_with(True))
    FALSE = pp.CaselessKeyword("false").set_parse_action(pp.replace_with(False))
    NULL = pp.CaselessKeyword("null").set_parse_action(pp.replace_with(None))

    # Values
    number = pp.common.number().set_name("number")
    quoted_string = pp.dbl_quoted_string().set_parse_action(pp.remove_quotes)
    single_quoted_string = pp.Regex(r"'[^']*'").set_parse_action(lambda t: t[0][1:-1])
    string_value = (quoted_string | single_quoted_string).set_name("string")
    value = (TRUE | FALSE | NULL | number | string_value).set_name("value")

    # Field names (support dot notation for nested access)
    identifier = pp.Word(pp.alphas + "_", pp.alphanums + "_").set_name("identifier")
    field = pp.Combine(identifier + pp.ZeroOrMore("." + identifier)).set_name("field")

    # Comparison expression
    comparison = pp.Group(
        field("field") + comparison_op("op") + value("value")
    ).set_name("comparison")

    # Use infix_notation for proper AND/OR precedence
    expr = pp.infix_notation(
        comparison,
        [
            (AND, 2, pp.opAssoc.LEFT, lambda t: ("AND", t[0][0::2])),
            (OR, 2, pp.opAssoc.LEFT, lambda t: ("OR", t[0][0::2])),
        ],
    )

    return expr


_PARSER = _build_parser()


# --- Comparison Evaluators ---

def _get_field_value(record: NamedTuple, field: str) -> Any:
    """Get field value from record, supporting dot notation."""
    value: Any = record
    for part in field.split("."):
        if hasattr(value, part):
            value = getattr(value, part)
        elif hasattr(value, "_asdict"):
            value = value._asdict().get(part)
        elif isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def _compare(field_value: Any, op: str, target_value: Any) -> bool:
    """Perform comparison operation."""
    # Handle None comparisons
    if field_value is None and target_value is None:
        return op in ("==", ">=", "<=")
    if field_value is None or target_value is None:
        return op == "!="

    # Type coercion for string comparisons
    if isinstance(target_value, str) and not isinstance(field_value, str):
        field_value = str(field_value)

    try:
        match op:
            case "==":
                return field_value == target_value
            case "!=":
                return field_value != target_value
            case ">":
                return field_value > target_value
            case ">=":
                return field_value >= target_value
            case "<":
                return field_value < target_value
            case "<=":
                return field_value <= target_value
            case _:
                return False
    except TypeError:
        return False


def _evaluate(parsed: Any, record: NamedTuple) -> bool:
    """Recursively evaluate parsed expression against record."""
    # Handle AND/OR tuples from infix_notation parse actions
    if isinstance(parsed, tuple) and len(parsed) == 2:
        op, terms = parsed
        results = [_evaluate(term, record) for term in terms]
        if op == "AND":
            return all(results)
        elif op == "OR":
            return any(results)

    # Single comparison (ParseResults with field/op/value)
    if isinstance(parsed, pp.ParseResults) and "field" in parsed:
        field_value = _get_field_value(record, str(parsed["field"]))
        return _compare(field_value, str(parsed["op"]), parsed["value"])

    # List of terms (single comparison wrapped in list)
    if isinstance(parsed, (list, pp.ParseResults)):
        for item in parsed:
            return _evaluate(item, record)

    return True


# --- Filter Classes ---

class ExpressionFilter:
    """Filter records using a parsed expression."""

    def __init__(self, expression: str):
        self.expression = expression
        self._parsed = _PARSER.parse_string(expression, parse_all=True)

    def __call__(self, record: NamedTuple) -> NamedTuple | None:
        if _evaluate(self._parsed, record):
            return None  # Drop matching records
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
            result = f(record)
            if result is None:
                return None
            record = result
        return record


# --- CLI Parsing Helpers ---

def parse_filter(expression: str) -> ExpressionFilter:
    """Parse a filter expression string."""
    return ExpressionFilter(expression)


def parse_unset(values: list[str]) -> UnsetFields | None:
    """Parse --unset field1,field2 arguments into UnsetFields filter."""
    fields = [f.strip() for value in values for f in value.split(",") if f.strip()]
    return UnsetFields(fields) if fields else None
