CREATE TABLE artist (
    id INTEGER PRIMARY KEY,
    name TEXT,
    real_name TEXT,
    profile TEXT,
    data_quality TEXT,
    urls TEXT,
    name_variations TEXT
);

CREATE TABLE artist_alias (
    artist_id INTEGER NOT NULL,
    id INTEGER,
    name TEXT
);

CREATE TABLE artist_group (
    artist_id INTEGER NOT NULL,
    id INTEGER,
    name TEXT
);

CREATE TABLE artist_member (
    artist_id INTEGER NOT NULL,
    id INTEGER,
    name TEXT
);
