CREATE TABLE label (
    id BIGINT PRIMARY KEY,
    name TEXT,
    contact_info TEXT,
    profile TEXT,
    data_quality TEXT,
    urls TEXT,
    parent_label TEXT
);

CREATE TABLE label_sublabel (
    label_id BIGINT NOT NULL,
    id BIGINT,
    name TEXT
);
