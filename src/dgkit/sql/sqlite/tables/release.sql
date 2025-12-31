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
