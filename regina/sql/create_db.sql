CREATE TABLE IF NOT EXISTS visitor(
    visitor_id  INTEGER PRIMARY KEY,
    platform    TEXT,
    browser     TEXT,
    is_human    INTEGER,
    range_id    INTEGER
) STRICT;

CREATE TABLE IF NOT EXISTS request(
    request_id  INTEGER PRIMARY KEY,
    visitor_id  INTEGER,
    FOREIGN KEY(visitor_id) REFERENCES visitor(visitor_id),
    group_id    INTEGER,
    FOREIGN KEY(group_id) REFERENCES filegroup(group_id),
    date        INTEGER,
    referer     TEXT,
    status      INTEGER
) STRICT;

CREATE TABLE IF NOT EXISTS filegroup(
    group_id    INTEGER PRIMARY KEY,
    groupname   TEXT
) STRICT;
CREATE TABLE IF NOT EXISTS file(
    filename    TEXT,
    group_id    INTEGER,
    FOREIGN KEY(group_id) REFERENCES filegroup(group_id)
) STRICT;

CREATE TABLE IF NOT EXISTS ip_range(
    range_id    INTEGER PRIMARY KEY,
    from        INTEGER,
    to          INTEGER,
    city_id     INTEGER,
    FOREIGN KEY(city_id) REFERENCES city(city_id)
) STRICT;

CREATE TABLE IF NOT EXISTS city(
    city        INTEGER PRIMARY KEY,
    name        TEXT,
    region      TEXT,
    country_id  INTEGER,
    FOREIGN KEY(country_id) REFERENCES country(country_id)
) STRICT;

CREATE TABLE IF NOT EXISTS country(
    country_id  INTEGER PRIMARY KEY,
    name        TEXT,
    code        TEXT
) STRICT;
