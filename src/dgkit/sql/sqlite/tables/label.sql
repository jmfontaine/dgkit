CREATE TABLE label (
    id INTEGER PRIMARY KEY,
    name TEXT,
    contact_info TEXT,
    profile TEXT,
    data_quality TEXT,
    urls TEXT,
    parent_label TEXT
);

CREATE TABLE label_sublabel (
    label_id INTEGER NOT NULL,
    id INTEGER,
    name TEXT
);
