-- see database.uxf
CREATE TABLE IF NOT EXISTS visitor(
    visitor_id  INTEGER PRIMARY KEY,
    ip_address  INTEGER,
    ip_range_id INTEGER,
    platform_id INTEGER,
    browser_id  INTEGER,
    is_human    INTEGER,
    is_mobile   INTEGER,
    FOREIGN KEY(platform_id) REFERENCES platform(platform_id),
    FOREIGN KEY(browser_id) REFERENCES browser(browser_id),
    FOREIGN KEY(ip_range_id) REFERENCES ip_range(ip_range_id)
) STRICT;

CREATE TABLE IF NOT EXISTS platform(
    platform_id INTEGER PRIMARY KEY,
    name        TEXT UNIQUE
) STRICT;

CREATE TABLE IF NOT EXISTS browser(
    browser_id  INTEGER PRIMARY KEY,
    name        TEXT UNIQUE
) STRICT;


-- REQUEST
CREATE TABLE IF NOT EXISTS request(
    request_id  INTEGER PRIMARY KEY,
    visitor_id  INTEGER,
    route_id    INTEGER,
    referer_id  INTEGER,
    time        INTEGER,
    status      INTEGER,
    FOREIGN KEY(visitor_id) REFERENCES visitor(visitor_id),
    FOREIGN KEY(route_id) REFERENCES route(route_id),
    FOREIGN KEY(referer_id) REFERENCES referer(referer_id)
) STRICT;

CREATE TABLE IF NOT EXISTS referer(
    referer_id  INTEGER PRIMARY KEY,
    name        TEXT UNIQUE
) STRICT;

CREATE TABLE IF NOT EXISTS route(
    route_id    INTEGER PRIMARY KEY,
    name        TEXT UNIQUE
) STRICT;


-- GEOIP
CREATE TABLE IF NOT EXISTS ip_range(
    ip_range_id INTEGER PRIMARY KEY,
    low         INTEGER UNIQUE,
    high        INTEGER UNIQUE,
    city_id     INTEGER,
    FOREIGN KEY(city_id) REFERENCES city(city_id)
) STRICT;

CREATE TABLE IF NOT EXISTS city(
    city_id     INTEGER PRIMARY KEY,
    name        TEXT,
    region_id   INTEGER,
    country_id  INTEGER,
    FOREIGN KEY(region_id) REFERENCES region(region_id),
    FOREIGN KEY(country_id) REFERENCES country(country_id)
) STRICT;

CREATE TABLE IF NOT EXISTS region(
    region_id   INTEGER PRIMARY KEY,
    name        TEXT,
    country_id  INTEGER,
    FOREIGN KEY(country_id) REFERENCES country(country_id)
) STRICT;

CREATE TABLE IF NOT EXISTS country(
    country_id  INTEGER PRIMARY KEY,
    name        TEXT UNIQUE,
    code        TEXT UNIQUE
) STRICT;

-- indexes for rankings
CREATE INDEX visitors_human_idx ON visitor(is_human);
CREATE INDEX visitors_ip_range_idx ON visitor(ip_range_id);
CREATE INDEX visitors_ip_range_human_idx ON visitor(is_human, ip_range_id);
CREATE INDEX requests_visitor_time_idx ON request(visitor_id, time);
