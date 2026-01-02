# Coding Style

## Alphabetical Ordering

Prefer alphabetical ordering for:

- Class attributes/properties
- CLI options and arguments
- Database tables
- Dictionary keys
- Enum members
- Function/method definitions within a class
- Import statements
- just recipes
- Keyword arguments in function/method calls
- Keyword arguments in class instantiations

Exceptions:

- `id` field always comes first in database tables and model classes
- Fields with default values must follow fields without defaults (Python requirement)
- Positional arguments maintain their required order

## Field Naming

Use descriptive names in models, even if XML uses abbreviations:

- `catalog_number` not `catno`
- `quantity` not `qty`
- `artist_name_variation` not `anv`

## CLI Options

Prefer long-form options (`--format`) over short-form (`-f`) in documentation and examples for clarity.

## Avoid Type Ignores

Do not use `# type: ignore` comments. They hide real issues and accumulate technical debt. Instead:

- Use `TypeGuard` for runtime type narrowing
- Use `Protocol` for structural typing
- Use `cast()` when the type system cannot express a known-safe pattern:
  - TypeGuard narrowing in ternary expressions
  - `LiteralString` for SQL loaded from trusted package resources
  - Protocol types after TypeGuard checks when narrowing fails
- Refactor code to make types explicit

If a type ignore seems necessary, investigate whether the code design can be improved first.
