# Notes

## UX Issues

- The format should be passed as an option (`--format, -f`) instead of as the first argument.
- The database writers (ie PostgreSQL and SQLite) should not be used by the `convert` but by the `load` command (to be created). Mixing both would result is a lot of unrelated options (e.g., what does the port mean for a file writer and what the compression mean for a database?).

## Improvements

- The `convert` and `load` commands should accept a `--read-chunk-size` option that takes a number of bytes to tweak how much is read from the input file at a time. It should default to 1MB.
- We should have a `benchmark` command that instruments the code and provides helpful insights to tweak the options to get the best performance for the current system. Or should it be an option on the `convert` and `load` command? The idea behind this is that users will likely convert/load the new dumps every month so being able to tweak it to get the best performance could be help ful, It would alo help me improve the performance, spot regressions, and improve the heuristics I want to introduce to provide fast defaults on most systems.
- I want the database schemas to be stored as SQL files alongside the source code fo easier review and updates. Table creation, and primary/foreign keys and indices should be in separate files.
- The database writer should create primary/foreign keys and indices after the tables have been created and data inserted.
- Add a `--batch-size, -b` to the `convert` and `load` commands to set the number of the records to write at once. Default to 10,000.
- The `inspect` command should provide meaningful information about the files. We might want to provide an option to inspect the records in the files but it should be disabled by default because it would take much longer. Maybe the Console writer should be part of that command.
- Implement splitting some models to a few records in the database writer when storing them as lists is not possible or efficient.
- Review the database schemas and file formats to ensure that the decisions made help querying the data easy and fast. If there is a trade-off to be made between ingestion and query speed, query speed should prevail.
- Allow selecting alternative readers that leverage other libraries and approaches that might perform better on some systems? (e.g., RapidGzip).
- Add a progress bar.

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
- Have the `--summary` option measure the number of XML elements processed to align with the `--limit` option and avoid having a limit of 1000 but see 2345 records processed in the summary which is confusing.

### v0.1.0
- Add PostgreSQL writer
- Finalize models
- Test UX
- Review code
- Run linters
- Update tests
- Create QA pipeline
- Create publish pipeline
- Package release

### v0.2.0
- Benchmark against alternatives

### v0.3.0
- Add `query` command to run a query against a converted file format or exported database.