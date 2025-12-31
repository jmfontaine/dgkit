CREATE TABLE release (
    id INTEGER PRIMARY KEY,
    status TEXT,
    title TEXT,
    country TEXT,
    released TEXT,
    notes TEXT,
    data_quality TEXT,
    master_id INTEGER,
    is_main_release INTEGER
);

CREATE TABLE release_artist (
    release_id INTEGER NOT NULL,
    id INTEGER NOT NULL,
    name TEXT NOT NULL,
    artist_name_variation TEXT,
    "join" TEXT
);

CREATE TABLE release_company (
    release_id INTEGER NOT NULL,
    id INTEGER NOT NULL,
    name TEXT NOT NULL,
    catalog_number TEXT,
    entity_type INTEGER,
    entity_type_name TEXT
);

CREATE TABLE release_extraartist (
    release_id INTEGER NOT NULL,
    id INTEGER,
    name TEXT NOT NULL,
    artist_name_variation TEXT,
    role TEXT,
    tracks TEXT
);

CREATE TABLE release_format (
    release_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    text TEXT,
    descriptions TEXT
);

CREATE TABLE release_genre (
    release_id INTEGER NOT NULL,
    genre TEXT NOT NULL
);

CREATE TABLE release_identifier (
    release_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    value TEXT NOT NULL
);

CREATE TABLE release_label (
    release_id INTEGER NOT NULL,
    id INTEGER NOT NULL,
    name TEXT NOT NULL,
    catalog_number TEXT
);

CREATE TABLE release_series (
    release_id INTEGER NOT NULL,
    id INTEGER NOT NULL,
    name TEXT NOT NULL,
    catalog_number TEXT
);

CREATE TABLE release_style (
    release_id INTEGER NOT NULL,
    style TEXT NOT NULL
);

CREATE TABLE release_track (
    release_id INTEGER NOT NULL,
    position TEXT,
    title TEXT,
    duration TEXT,
    artists TEXT,
    extra_artists TEXT,
    sub_tracks TEXT
);

CREATE TABLE release_video (
    release_id INTEGER NOT NULL,
    src TEXT NOT NULL,
    duration INTEGER NOT NULL,
    embed INTEGER NOT NULL,
    title TEXT,
    description TEXT
);
