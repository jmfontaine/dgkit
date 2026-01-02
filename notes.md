# Notes

## UX Issues

- The format should be passed as an option (`--format, -f`) instead of as the first argument.
- The database writers (ie PostgreSQL and SQLite) should not be used by the `convert` but by the `load` command (to be created). Mixing both would result is a lot of unrelated options (e.g., what does the port mean for a file writer and what the compression mean for a database?).

## Improvements

- The `convert` and `load` commands should accept a `--read-chunk-size` option that takes a number of bytes to tweak how much is read from the input file at a time. It should default to 1MB.
- We should have a `benchmark` command that instruments the code and provides helpful insights to tweak the options to get the best performance for the current system. Or should it be an option on the `convert` and `load` command? The idea behind this is that users will likely convert/load the new dumps every month so being able to tweak it to get the best performance could be help full, It would also help me improve the performance, spot regressions, and improve the heuristics I want to introduce to provide fast defaults on most systems.
- I want the database schemas to be stored as SQL files alongside the source code for easier review and updates. Table creation, and primary/foreign keys and indices should be in separate files.
- The database writer should create primary/foreign keys and indices after the tables have been created and data inserted.
- Add a `--batch-size, -b` to the `convert` and `load` commands to set the number of the records to write at once. Default to 10,000.
- The `inspect` command should provide meaningful information about the files. We might want to provide an option to inspect the records in the files but it should be disabled by default because it would take much longer. Maybe the Console writer should be part of that command.
- Implement splitting some models to a few records in the database writer when storing them as lists is not possible or efficient.
- Review the database schemas and file formats to ensure that the decisions made help querying the data easy and fast. If there is a trade-off to be made between ingestion and query speed, query speed should prevail.
- Allow selecting alternative readers that leverage other libraries and approaches that might perform better on some systems? (e.g., RapidGzip).
- Add a progress bar.
- Have the `--summary` option measure the number of XML elements processed to align with the `--limit` option and avoid having a limit of 1000 but see 2345 records processed in the summary which is confusing.
- Create a vanilla JSON format writer.

## Questions

- In a command, how could we organize the options that relate to the reader vs to the writer? Should we use a naming convention, should we group them in the help screen using Typer's help panels? Should we do something different? Should we just ignore this?
- Should the Blackhole writer be hidden since it might just confuse people and be enabled when a special value or option is passed?
- How could we provide filtering data before writing it? (e.g., dropping a record that matches some value or pattern, unsetting some properties of a record to ignore some of its data but still write the remaining data for that record) Should we switch to data classes or should we convert the named tuple to another named tuple?
- How can we organize tests to ensure that changes don't introduce bugs nor performance regression?
- How can we reliably and fairly benchmark dgkit against alternatives?
- How do we ensure that there are no memory leaks?
- How do we make sure that dgkit run on as many systems as possible?
- How do we publish to PyPi?
- How do we publish to Homebrew?
- How do we allow deploying with uvx?
- How do we allow deploying with pipx?
- Are there other popular and relevant deployment methods we should offer?
- Should we distribute dgkit as a standalone binary?
- How do we test dgkit on Linux and Windows machines (the author works on a Mac)?
- How do we design the GitHub Actions workflows to achieve all of our goals in terms of QA and deployments?
- Should the `load` command take a DSN string as input or options (e.g., --host --db --user --port --pwd)?
- The parsers should not yield multiple record types. Each entity type should be a single record. It is up to the writers to split that record into multiple records if required by the destination. Splitting records up at the parser level means that writers that can handle records with nested data have to merge the records back.
- Maybe the SQLite writer should not use `--dsn` but `--path`.
- How to best provide various levels of information to the user about operations?
- How to check if the XML element has nodes or attributes we did not extract to the model? I want to make sure that the model represents the raw XML data accurately. Discogs data can be weird at times so I would like to have a way to catch unhandled edge cases. I am afraid it would hurt performance so it might have to be an option that is disabled by default. Maybe `--paranoia` or `--thorough`.
- How to handle property values that are actually enums in disguise? For example the `dataquality` property has a small fixed number of values. Storing them as string is a waste of space.
- Should we have logging? Maybe for debugging or tracking performance?
- Will users really import input files independently or should we always process all of them? Could they only care in a single entity type (e.g., artists)? Would that even make sense? Should the default behavior be to process all files, unless an option is passed to ignored some of them?

## Next Items

- Should we offer an option to normalize the data in the file writers to avoid bloating them with duplicated data?
- In the database writers, create views for entity types that are not explicitly defined but whose data is spread over other entities (e.g., series whose data is available in releases).
- How could we resume stopped imports?
- Create a Discogs stats report over time.

- Test UX and document usage
- Review code and document architecture and design decisions in CLAUDE.md
- Test dgkit with all 2025 dumps, and possibly dumps from previous years.

### v0.1.0 - Foundations

- Add PostgreSQL writer
- Clean messaging on failure (no debug trace unless enabled by the user)
- Finalize models
- Run linters
- Test UX

- Benchmark against alternatives
- Review code
- Update tests
- Enable dependable.
- Create QA pipeline
- Create publish pipeline
- Create CLAUDE.md file
- Add a nice screenshot to the top of the READE file (see <https://github.com/chaosprint/hindsight>).
- Package release

### v0.2.0 - Performance Tuning

- Optimize imports for optional features
- Look into multi-processing
- Research JSON libraries

### v0.3.0 - Additional Features

- Add `query` command to run a query against a converted file format or exported database
- Implement and document auto-completion.
- Test Python versions compatibility.
- Test PostgreSQL versions compatibility.
- Add support for Parquet file format.

### v0.4.0 - Optimized Deployment

- Release package variant with unusual dependencies

### v0.5.0 - UX Improvements

- Implement best practices from <https://clig.dev/> and <https://medium.com/@jdxcode/12-factor-cli-apps-dd3c227a0e46>
- Omit Modified and Dropped from the summary when no filters were passed.
