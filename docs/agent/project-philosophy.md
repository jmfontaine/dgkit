# Project Philosophy

## Guiding Principles

- Incremental progress over big bangs: Make small changes that run and pass tests.
- Learning from existing code: Study and plan before implementing.
- Pragmatic over dogmatic: Adapt to the project's reality.
- Clear intent over clever code: Be boring and obvious.

## Simplicity

- Don't add features speculatively.
- Add complexity only when there's a demonstrated need.
- Keep a single responsibility per class, function, and method.
- Avoid premature abstractions.
- No clever tricks. If you need to explain it, it's too complex.

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
