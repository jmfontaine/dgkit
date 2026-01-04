CREATE TABLE artist (
    id BIGINT PRIMARY KEY,
    name TEXT,
    real_name TEXT,
    profile TEXT,
    data_quality TEXT,
    urls TEXT,
    name_variations TEXT
);

CREATE TABLE artist_alias (
    artist_id BIGINT NOT NULL,
    id BIGINT,
    name TEXT
);

CREATE TABLE artist_group (
    artist_id BIGINT NOT NULL,
    id BIGINT,
    name TEXT
);

CREATE TABLE artist_member (
    artist_id BIGINT NOT NULL,
    id BIGINT,
    name TEXT
);
