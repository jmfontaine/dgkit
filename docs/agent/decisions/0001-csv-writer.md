---
date: 2025-12-31
status: Accepted
---

# CSV Format Not Supported

## Context and Problem Statement

CSV is a popular file format with extensive tooling. It is supported by some
alternatives to dgkit (e.g., [discogs-xml2db](https://github.com/philipmat/discogs-xml2db/tree/develop?tab=readme-ov-file#converting-dumps-to-csv))
, so should dgkit support it too?

## Considered Options

- Add a CSV writer
- Don't add a CSV writer

## Decision Outcome

Chosen option: "Do not add a CSV writer", because:

- CSV is a flat format, but Discogs entities contain nested data.
- Saving nested data to CSV requires one of these approaches:
  - Encode nested data as JSON strings, mixing formats and complicating processing.
  - Save each record across multiple rows, creating confusion and processing
        difficulties.
  - Split data into multiple files, requiring users to rebuild relationships later.
- CSV isn't a good fit for Discogs data, and supporting it would create a poor
    user experience. We recommend using formats that natively support nested data,
    such as JSON.

### Consequences

- Users who want to convert Discogs data to CSV will need to first convert it to
    a format supported by dgkit, then convert that to CSV, adding an extra step to
    their workflow.
