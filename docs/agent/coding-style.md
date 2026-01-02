# Coding Style

## Alphabetical Ordering

Prefer alphabetical ordering for:

- Enum members
- Class attributes/properties
- Function/method definitions within a class
- Import statements
- Dictionary keys
- CLI arguments (where possible)
- Keyword arguments in function/method calls
- Keyword arguments in class instantiations
- Database tables

Exceptions:

- `id` field always comes first in database tables and model classes
- Fields with default values must follow fields without defaults (Python requirement)
- Positional arguments maintain their required order

## Field Naming

Use descriptive names in models, even if XML uses abbreviations:

- `catalog_number` not `catno`
- `quantity` not `qty`
- `artist_name_variation` not `anv`
