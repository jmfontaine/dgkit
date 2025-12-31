CREATE TABLE masterrelease (
    id BIGINT PRIMARY KEY,
    title TEXT,
    main_release BIGINT,
    year BIGINT,
    notes TEXT,
    data_quality TEXT
);

CREATE TABLE masterrelease_artist (
    masterrelease_id BIGINT NOT NULL,
    id BIGINT NOT NULL,
    name TEXT NOT NULL,
    artist_name_variation TEXT,
    "join" TEXT
);

CREATE TABLE masterrelease_genre (
    masterrelease_id BIGINT NOT NULL,
    genre TEXT NOT NULL
);

CREATE TABLE masterrelease_style (
    masterrelease_id BIGINT NOT NULL,
    style TEXT NOT NULL
);

CREATE TABLE masterrelease_video (
    masterrelease_id BIGINT NOT NULL,
    src TEXT NOT NULL,
    duration BIGINT NOT NULL,
    embed BIGINT NOT NULL,
    title TEXT,
    description TEXT
);
