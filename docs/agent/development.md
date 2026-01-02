# Development

## Setup

Run `just setup` to install dependencies and configure git hooks.

## Commands

Run via `just <command>`:

| Command | Purpose |
|---------|---------|
| `check` | Run all checks (lint, typecheck, test) |
| `format` | Format all source files |
| `fix` | Auto-fix linting issues |
| `lint` | Check for defects |
| `test` | Run tests with coverage |
| `typecheck` | Type check source code |
| `clean` | Remove build artifacts |
| `docs` | Regenerate README |

## Workflow

- Run `just check` before committing
- Run `just format` after making changes
- Run `just fix` to auto-fix linting issues before manual fixes
