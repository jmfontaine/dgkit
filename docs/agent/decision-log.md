# Decision Log

Decisions follow the [MADR](https://adr.github.io/madr/) format.

| ID | Decision | Status |
|----|----------|--------|
| [0001](decisions/0001-csv-writer.md) | CSV format not supported due to poor fit for nested data | Accepted |
| [0002](decisions/0002-parser-performance-optimizations.md) | Parser optimizations: slotted dataclasses, inlined functions, single-pass iteration | Accepted |
| [0003](decisions/0003-pipeline-concurrency-architecture.md) | Pipeline concurrency: multiprocess+dicts wins (+24-56%), but baseline kept for simplicity | Accepted |
