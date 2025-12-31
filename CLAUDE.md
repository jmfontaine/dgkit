# CLAUDE.md

Guidelines for AI assistants working on dgkit.

## Project Philosophy

### Fail Early, Fail Hard

Do not silently ingest bad data. The user does not trust Discogs data quality. Validation errors should surface immediately at parse time, not propagate through the system.

Use `--strict` and `--fail-on-unhandled` flags to enforce this. When in doubt, reject rather than accept.

### Explicit Over Implicit

- No magic auto-discovery of files. Users specify exactly what they want to process.
- Shell globs provide flexibility without adding framework complexity.
- Unix-like composability: do one thing well, let users combine tools.

### YAGNI (You Aren't Gonna Need It)

Do not add features speculatively. Examples of rejected features:
- CSV export (poor fit for nested data; SQLite covers this use case)
- Logging infrastructure (current feedback mechanisms suffice)
- Auto-discovery of input files (shell globs work fine)
- Country enum (300+ values, dropdown-constrained, low risk of bad data)

Add complexity only when there's a demonstrated need.

### Performance Claims Require Benchmarks

Do not optimize based on speculation. If a design decision is questioned for performance reasons, measure first. XML parsing and I/O typically dominate; micro-optimizations elsewhere rarely matter.

### Avoid Type Ignores

Do not use `# type: ignore` comments. They hide real issues and accumulate technical debt. Instead:
- Use `TypeGuard` for runtime type narrowing
- Use `Protocol` for structural typing
- Use `cast()` when the type system cannot express a known-safe pattern:
  - TypeGuard narrowing in ternary expressions
  - `LiteralString` for SQL loaded from trusted package resources
  - Protocol types after TypeGuard checks when narrowing fails
- Refactor code to make types explicit

If a type ignore seems necessary, investigate whether the code design can be improved first.

## Design Guidelines

### Enums for Fixed Values

Use `StrEnum` for fields with small, fixed sets of values where validation matters:
- `DataQuality` (6 values)
- `ReleaseStatus` (4 values)
- `IdentifierType` (11 values)
- `FormatName` (~35 values)

Do NOT use enums when:
- The value set is large (100+)
- Values come from constrained UI (dropdowns) where bad data is unlikely
- The maintenance burden outweighs validation benefit

### Alphabetical Ordering

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

### Field Naming

Use descriptive names in models, even if XML uses abbreviations:
- `catalog_number` not `catno`
- `quantity` not `qty`
- `artist_name_variation` not `anv`

### Output Format Selection

| Need | Format |
|------|--------|
| Human inspection | `console` |
| Flat file with nested data | `json`, `jsonl` |
| Queryable database | `sqlite`, `postgresql` |

CSV is not supported. Nested/relational data does not fit flat formats. Users needing CSV can query SQLite and export results.

### Parser Responsibility

Parsers extract and validate data from XML. They convert to typed models with enums where appropriate. Validation happens once, at parse time.

### Writer Responsibility

Writers serialize models to output formats. They should not need to re-validate. Database writers handle batching and schema creation.

## Communication Style

- Be direct and concise
- Lead with answers, skip preamble
- Present tradeoffs clearly
- Recommend a path forward
- When uncertain, ask rather than guess
