# Project Philosophy

## Provide Great User Experience

- Provide meaningful and helpful guidance to the user.
- Provide sane defaults to optimize the performance on the user system.

## Fail Early, Fail Hard

- Bad data is the worst. Discogs data can be inconsistent. Do not silently ingest bad data. Validation errors should surface immediately at parse time, not propagate through the system. When in doubt, reject with a helpful error message rather than accept.

## Work Everywhere

- Design dgkit to work on as many systems as possible.
- Make optimizations that could limit compatibility optional.

## Be Fast Within Reason

- Use every trick in the book to get the data from Discogs data dump files to where the user needs it.
- Generally, the less data manipulation is done, the faster the pipeline.
- Do not optimize based on speculation. If a design decision is questioned for performance reasons, measure first
- Beware of micro-optimizations that complicate the code for marginal gains.

## Explicit Over Implicit

- No magic auto-discovery of files. Users specify exactly what they want to process.
- Shell globs provide flexibility without adding framework complexity.
- Unix-like composability: do one thing well, let users combine tools.

## YAGNI (You Aren't Gonna Need It)

- Do not add features speculatively.

Examples of rejected features:

- CSV export (poor fit for nested data; SQLite covers this use case)
- Logging infrastructure (current feedback mechanisms suffice)
- Auto-discovery of input files (shell globs work fine)
- Country enum (300+ values, dropdown-constrained, low risk of bad data)

Add complexity only when there's a demonstrated need.

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
