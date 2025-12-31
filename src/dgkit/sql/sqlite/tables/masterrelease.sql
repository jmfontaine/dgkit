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
    id INTEGER NOT NULL,
    name TEXT NOT NULL,
    artist_name_variation TEXT,
    "join" TEXT
);

CREATE TABLE masterrelease_genre (
    masterrelease_id INTEGER NOT NULL,
    genre TEXT NOT NULL
);

CREATE TABLE masterrelease_style (
    masterrelease_id INTEGER NOT NULL,
    style TEXT NOT NULL
);

CREATE TABLE masterrelease_video (
    masterrelease_id INTEGER NOT NULL,
    src TEXT NOT NULL,
    duration INTEGER NOT NULL,
    embed INTEGER NOT NULL,
    title TEXT,
    description TEXT
);
