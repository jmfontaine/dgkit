CREATE TABLE masterrelease (
    id INTEGER PRIMARY KEY,
    title TEXT,
    main_release INTEGER,
    year INTEGER,
    notes TEXT,
    data_quality TEXT
);

CREATE TABLE masterrelease_artist (
    masterrelease_id INTEGER NOT NULL,
    id INTEGER,
    name TEXT,
    artist_name_variation TEXT,
    "join" TEXT
);

CREATE TABLE masterrelease_genre (
    masterrelease_id INTEGER NOT NULL,
    genre TEXT
);

CREATE TABLE masterrelease_style (
    masterrelease_id INTEGER NOT NULL,
    style TEXT
);

CREATE TABLE masterrelease_video (
    masterrelease_id INTEGER NOT NULL,
    src TEXT,
    duration INTEGER,
    embed INTEGER,
    title TEXT,
    description TEXT
);
