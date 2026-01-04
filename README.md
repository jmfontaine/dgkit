# dgkit

A fast, easy-to-use tool for converting, and loading data from [Discogs data dumps](https://www.discogs.com/data/) into various formats and databases.

![Demo](docs/user/assets/demo.gif)

## Installation

TODO

## Usage

<!-- [[[cog
import cog
from typer.testing import CliRunner
from dgkit.cli import app

runner = CliRunner()
result = runner.invoke(app, ["--help"], prog_name="dgkit", env={"COLUMNS": "88"})
cog.out("```text\n{}```".format(result.output))
]]] -->
```text
                                                                                        
 Usage: dgkit [OPTIONS] COMMAND [ARGS]...                                               
                                                                                        
 Process Discogs data dumps.                                                            
                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────╮
│ --debug                       Show full error tracebacks.                            │
│ --install-completion          Install completion for the current shell.              │
│ --show-completion             Show completion for the current shell, to copy it or   │
│                               customize the installation.                            │
│ --help                        Show this message and exit.                            │
╰──────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────╮
│ convert   Convert data dumps to another format.                                      │
│ load      Load data dumps into a database.                                           │
│ sample    Extract a sample from a Discogs data dump.                                 │
╰──────────────────────────────────────────────────────────────────────────────────────╯

```
<!-- [[[end]]] -->

### dgkit convert

Convert Discogs data dumps to various formats. Supports filtering records, limiting output, and optional compression.

| Option | Values |
|-----------------|-------------------------------|
| Output formats | `json`, `jsonl` |
| Compression | `bz2`, `gzip`, `none` |

<details>
<summary>Full command help</summary>

<!-- [[[cog
result = runner.invoke(app, ["convert", "--help"], prog_name="dgkit", env={"COLUMNS": "88"})
cog.out("```text\n{}```".format(result.output))
]]] -->
```text
                                                                                        
 Usage: dgkit convert [OPTIONS] FILES...                                                
                                                                                        
 Convert data dumps to another format.                                                  
                                                                                        
╭─ Arguments ──────────────────────────────────────────────────────────────────────────╮
│ *    files      FILES...  Discogs dump files. [required]                             │
╰──────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────╮
│ *  --format       -f                   [blackhole|console|js  Output file format.    │
│                                        on|jsonl]              [required]             │
│    --limit                             INTEGER                Max records per file.  │
│    --output-dir   -o                   PATH                   Output directory.      │
│                                                               [default: .]           │
│    --compress     -c                   [bz2|gzip|none]        Compression algorithm. │
│                                                               [default: none]        │
│    --overwrite    -w                                          Overwrite existing     │
│                                                               files.                 │
│    --type         -t                   [artists|labels|maste  Entity type (if not    │
│                                        rs|releases]           auto-detected).        │
│    --drop-if                           TEXT                   Drop records matching  │
│                                                               field=value.           │
│    --unset                             TEXT                   Fields to set to null  │
│                                                               (comma-separated).     │
│    --summary          --no-summary                            Show summary.          │
│                                                               [default: summary]     │
│    --progress         --no-progress                           Show progress bar.     │
│                                                               [default: progress]    │
│    --strict                                                   Warn about unhandled   │
│                                                               XML elements.          │
│    --strict-fail                                              Fail on unhandled XML  │
│                                                               data (implies          │
│                                                               --strict).             │
│    --help                                                     Show this message and  │
│                                                               exit.                  │
╰──────────────────────────────────────────────────────────────────────────────────────╯

```
<!-- [[[end]]] -->

</details>

#### Examples

<!-- [[[cog
from datetime import date

# Discogs creates snapshots on the 1st of each month
today = date.today()
snapshot = today.replace(day=1).strftime("%Y%m%d")

cog.out(f"""```shell
# Convert releases to JSONL format
dgkit convert -f jsonl discogs_{snapshot}_releases.xml.gz

# Convert to JSON with bzip2 compression
dgkit convert -f json -c bz2 discogs_{snapshot}_artists.xml.gz

# Convert first 1000 records only (useful for testing)
dgkit convert -f jsonl --limit 1000 discogs_{snapshot}_releases.xml.gz

# Drop records with specific data quality
dgkit convert -f jsonl --drop-if "data_quality=Needs Vote" discogs_{snapshot}_releases.xml.gz

# Clear specific fields from output
dgkit convert -f jsonl --unset notes,images discogs_{snapshot}_releases.xml.gz

# Validate XML for unhandled elements
dgkit convert -f jsonl --strict discogs_{snapshot}_releases.xml.gz

# Fail on any unhandled XML data
dgkit convert -f jsonl --strict-fail discogs_{snapshot}_releases.xml.gz

# Convert multiple files
dgkit convert -f jsonl discogs_{snapshot}_artists.xml.gz discogs_{snapshot}_labels.xml.gz discogs_{snapshot}_releases.xml.gz

# Convert all XML files using a wildcard
dgkit convert -f jsonl discogs_{snapshot}_*.xml.gz

# Convert a file with entity type in filename (auto-detected)
dgkit convert -f jsonl my_releases_backup.xml.gz

# Explicit type override when filename has no entity type
dgkit convert -f jsonl --type releases dump.xml.gz
```""")
]]] -->
```shell
# Convert releases to JSONL format
dgkit convert -f jsonl discogs_20260101_releases.xml.gz

# Convert to JSON with bzip2 compression
dgkit convert -f json -c bz2 discogs_20260101_artists.xml.gz

# Convert first 1000 records only (useful for testing)
dgkit convert -f jsonl --limit 1000 discogs_20260101_releases.xml.gz

# Drop records with specific data quality
dgkit convert -f jsonl --drop-if "data_quality=Needs Vote" discogs_20260101_releases.xml.gz

# Clear specific fields from output
dgkit convert -f jsonl --unset notes,images discogs_20260101_releases.xml.gz

# Validate XML for unhandled elements
dgkit convert -f jsonl --strict discogs_20260101_releases.xml.gz

# Fail on any unhandled XML data
dgkit convert -f jsonl --strict-fail discogs_20260101_releases.xml.gz

# Convert multiple files
dgkit convert -f jsonl discogs_20260101_artists.xml.gz discogs_20260101_labels.xml.gz discogs_20260101_releases.xml.gz

# Convert all XML files using a wildcard
dgkit convert -f jsonl discogs_20260101_*.xml.gz

# Convert a file with entity type in filename (auto-detected)
dgkit convert -f jsonl my_releases_backup.xml.gz

# Explicit type override when filename has no entity type
dgkit convert -f jsonl --type releases dump.xml.gz
```
<!-- [[[end]]] -->

### dgkit load

Load Discogs data dumps directly into a database. Supports batched inserts, filtering, and schema auto-creation.

| Database | Versions |
|----------|----------|
| SQLite | 3.x |
| PostgreSQL | 14+ |

<details>
<summary>Full command help</summary>

<!-- [[[cog
result = runner.invoke(app, ["load", "--help"], prog_name="dgkit", env={"COLUMNS": "88"})
cog.out("```text\n{}```".format(result.output))
]]] -->
```text
                                                                                        
 Usage: dgkit load [OPTIONS] FILES...                                                   
                                                                                        
 Load data dumps into a database.                                                       
                                                                                        
╭─ Arguments ──────────────────────────────────────────────────────────────────────────╮
│ *    files      FILES...  Discogs dump files. [required]                             │
╰──────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────╮
│ --dsn                               TEXT                     Database connection     │
│                                                              string (PostgreSQL:     │
│                                                              postgresql://...,       │
│                                                              SQLite: path or         │
│                                                              sqlite:///...).         │
│ --limit                             INTEGER                  Max records per file.   │
│ --batch        -b                   INTEGER                  Batch size for database │
│                                                              inserts.                │
│                                                              [default: 10000]        │
│ --overwrite    -w                                            Overwrite existing      │
│                                                              database.               │
│ --type         -t                   [artists|labels|masters  Entity type (if not     │
│                                     |releases]               auto-detected).         │
│ --drop-if                           TEXT                     Drop records matching   │
│                                                              field=value.            │
│ --unset                             TEXT                     Fields to set to null   │
│                                                              (comma-separated).      │
│ --summary          --no-summary                              Show summary.           │
│                                                              [default: summary]      │
│ --progress         --no-progress                             Show progress bar.      │
│                                                              [default: progress]     │
│ --strict                                                     Warn about unhandled    │
│                                                              XML elements.           │
│ --strict-fail                                                Fail on unhandled XML   │
│                                                              data (implies           │
│                                                              --strict).              │
│ --help                                                       Show this message and   │
│                                                              exit.                   │
╰──────────────────────────────────────────────────────────────────────────────────────╯

```
<!-- [[[end]]] -->

</details>

#### Examples

<!-- [[[cog
cog.out(f"""```shell
# Load releases into SQLite (database name auto-generated from input files)
dgkit load discogs_{snapshot}_releases.xml.gz

# Load into a specific SQLite database
dgkit load --dsn discogs.db discogs_{snapshot}_releases.xml.gz

# Load into PostgreSQL
dgkit load --dsn "postgresql://user:pass@localhost/discogs" discogs_{snapshot}_releases.xml.gz

# Load first 1000 records only (useful for testing)
dgkit load --limit 1000 discogs_{snapshot}_releases.xml.gz

# Use smaller batch size for memory-constrained environments
dgkit load -b 1000 discogs_{snapshot}_releases.xml.gz

# Overwrite existing database without prompting
dgkit load -w discogs_{snapshot}_releases.xml.gz

# Load multiple entity types into the same database
dgkit load --dsn discogs.db discogs_{snapshot}_artists.xml.gz discogs_{snapshot}_labels.xml.gz discogs_{snapshot}_releases.xml.gz

# Load all dump files using a wildcard
dgkit load --dsn discogs.db discogs_{snapshot}_*.xml.gz

# Drop records with specific data quality
dgkit load --drop-if "data_quality=Needs Vote" discogs_{snapshot}_releases.xml.gz

# Clear specific fields before loading
dgkit load --unset notes,images discogs_{snapshot}_releases.xml.gz

# Validate XML for unhandled elements
dgkit load --strict discogs_{snapshot}_releases.xml.gz

# Fail on any unhandled XML data
dgkit load --strict-fail discogs_{snapshot}_releases.xml.gz

# Load a file with entity type in filename (auto-detected)
dgkit load my_releases_backup.xml.gz

# Explicit type override when filename has no entity type
dgkit load --type releases dump.xml.gz
```""")
]]] -->
```shell
# Load releases into SQLite (database name auto-generated from input files)
dgkit load discogs_20260101_releases.xml.gz

# Load into a specific SQLite database
dgkit load --dsn discogs.db discogs_20260101_releases.xml.gz

# Load into PostgreSQL
dgkit load --dsn "postgresql://user:pass@localhost/discogs" discogs_20260101_releases.xml.gz

# Load first 1000 records only (useful for testing)
dgkit load --limit 1000 discogs_20260101_releases.xml.gz

# Use smaller batch size for memory-constrained environments
dgkit load -b 1000 discogs_20260101_releases.xml.gz

# Overwrite existing database without prompting
dgkit load -w discogs_20260101_releases.xml.gz

# Load multiple entity types into the same database
dgkit load --dsn discogs.db discogs_20260101_artists.xml.gz discogs_20260101_labels.xml.gz discogs_20260101_releases.xml.gz

# Load all dump files using a wildcard
dgkit load --dsn discogs.db discogs_20260101_*.xml.gz

# Drop records with specific data quality
dgkit load --drop-if "data_quality=Needs Vote" discogs_20260101_releases.xml.gz

# Clear specific fields before loading
dgkit load --unset notes,images discogs_20260101_releases.xml.gz

# Validate XML for unhandled elements
dgkit load --strict discogs_20260101_releases.xml.gz

# Fail on any unhandled XML data
dgkit load --strict-fail discogs_20260101_releases.xml.gz

# Load a file with entity type in filename (auto-detected)
dgkit load my_releases_backup.xml.gz

# Explicit type override when filename has no entity type
dgkit load --type releases dump.xml.gz
```
<!-- [[[end]]] -->

## License

dgkit is licensed under the [Apache License 2.0](LICENSE.txt).
