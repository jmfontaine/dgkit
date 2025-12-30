# convert

```shell
# Will convert discogs_20251201_artists.xml.gz to JSONL and save the data to discogs_20251201_artists.jsonl
dgkit convert --format jsonl discogs_20251201_artists.xml.gz

# Will convert discogs_20251201_artists.xml.gz to JSONL and save the data in artists.jsonl
dgkit convert --format jsonl --output artists.jsonl discogs_20251201_artists.xml.gz

# Will convert discogs_20251201_artists.xml.gz and discogs_20251201_labels.xml.gz to JSONL and save the data to discogs_20251201_artists.jsonl and discogs_20251201_labels.jsonl, respectively
dgkit convert --format jsonl discogs_20251201_artists.xml.gz discogs_20251201_labels.xml.gz

# Will convert all the files matching discogs_20251201_*.xml.gz to JSONL and save the data to discogs_20251201_*.jsonl
dgkit convert --format jsonl discogs_20251201_*.xml.gz

# Will convert discogs_20251201_artists.xml.gz to JSONL and save the first 10,000 items to discogs_20251201_artists.jsonl.
dgkit convert --format jsonl --limit 10000 discogs_20251201_artists.xml.gz
```