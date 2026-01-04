CREATE TABLE "release" (
    id BIGINT PRIMARY KEY,
    status TEXT,
    title TEXT,
    country TEXT,
    released TEXT,
    notes TEXT,
    data_quality TEXT,
    master_id BIGINT,
    is_main_release BOOLEAN
);

CREATE TABLE release_artist (
    release_id BIGINT NOT NULL,
    id BIGINT,
    name TEXT,
    artist_name_variation TEXT,
    "join" TEXT
);

CREATE TABLE release_company (
    release_id BIGINT NOT NULL,
    id BIGINT,
    name TEXT,
    catalog_number TEXT,
    entity_type BIGINT,
    entity_type_name TEXT
);

CREATE TABLE release_extraartist (
    release_id BIGINT NOT NULL,
    id BIGINT,
    name TEXT,
    artist_name_variation TEXT,
    role TEXT,
    tracks TEXT
);

CREATE TABLE release_format (
    release_id BIGINT NOT NULL,
    name TEXT,
    quantity TEXT,
    text TEXT,
    descriptions TEXT []
);

CREATE TABLE release_genre (
    release_id BIGINT NOT NULL,
    genre TEXT
);

CREATE TABLE release_identifier (
    release_id BIGINT NOT NULL,
    type TEXT,
    description TEXT,
    value TEXT
);

CREATE TABLE release_label (
    release_id BIGINT NOT NULL,
    id BIGINT,
    name TEXT,
    catalog_number TEXT
);

CREATE TABLE release_series (
    release_id BIGINT NOT NULL,
    id BIGINT,
    name TEXT,
    catalog_number TEXT
);

CREATE TABLE release_style (
    release_id BIGINT NOT NULL,
    style TEXT
);

CREATE TABLE release_track (
    release_id BIGINT NOT NULL,
    position TEXT,
    title TEXT,
    duration TEXT,
    artists JSONB,
    extra_artists JSONB,
    sub_tracks JSONB
);

CREATE TABLE release_video (
    release_id BIGINT NOT NULL,
    description TEXT,
    duration BIGINT,
    embed BOOLEAN,
    src TEXT,
    title TEXT
);
