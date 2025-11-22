-- SQLite schema v2: normalized GTFS with precomputed service_day and schedules
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS feeds (
  feed_id INTEGER PRIMARY KEY AUTOINCREMENT,
  feed_name TEXT,
  feed_start_date TEXT,
  feed_end_date TEXT,
  feed_version TEXT,
  file_hash TEXT,
  loaded_at TEXT
);

CREATE TABLE IF NOT EXISTS routes (
  route_id TEXT PRIMARY KEY,
  feed_id INTEGER REFERENCES feeds(feed_id) ON DELETE CASCADE,
  route_short_name TEXT,
  route_long_name TEXT,
  route_desc TEXT,
  route_type INTEGER,
  route_color TEXT,
  route_text_color TEXT
);

CREATE TABLE IF NOT EXISTS stops (
  stop_id TEXT PRIMARY KEY,
  stop_name TEXT,
  stop_desc TEXT,
  stop_lat REAL,
  stop_lon REAL,
  zone_id TEXT,
  stop_url TEXT,
  location_type INTEGER,
  parent_station TEXT,
  platform_code TEXT,
  wheelchair_boarding INTEGER
);

CREATE TABLE IF NOT EXISTS services (
  service_id TEXT PRIMARY KEY,
  feed_id INTEGER REFERENCES feeds(feed_id) ON DELETE CASCADE,
  start_date TEXT,
  end_date TEXT,
  monday INTEGER DEFAULT 0,
  tuesday INTEGER DEFAULT 0,
  wednesday INTEGER DEFAULT 0,
  thursday INTEGER DEFAULT 0,
  friday INTEGER DEFAULT 0,
  saturday INTEGER DEFAULT 0,
  sunday INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS service_exceptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service_id TEXT,
  date TEXT,
  exception_type INTEGER,
  UNIQUE(service_id, date, exception_type)
);

CREATE TABLE IF NOT EXISTS trips (
  trip_id TEXT PRIMARY KEY,
  route_id TEXT,
  service_id TEXT,
  trip_headsign TEXT,
  direction_id INTEGER,
  block_id TEXT,
  shape_id TEXT,
  wheelchair_accessible INTEGER,
  bikes_allowed INTEGER,
  FOREIGN KEY(route_id) REFERENCES routes(route_id),
  FOREIGN KEY(service_id) REFERENCES services(service_id)
);

CREATE TABLE IF NOT EXISTS stop_times (
  stop_time_id INTEGER PRIMARY KEY AUTOINCREMENT,
  trip_id TEXT,
  stop_sequence INTEGER,
  arrival_time TEXT,
  departure_time TEXT,
  stop_id TEXT,
  pickup_type INTEGER,
  drop_off_type INTEGER,
  timepoint INTEGER,
  UNIQUE(trip_id, stop_sequence),
  FOREIGN KEY(trip_id) REFERENCES trips(trip_id),
  FOREIGN KEY(stop_id) REFERENCES stops(stop_id)
);

CREATE TABLE IF NOT EXISTS frequencies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trip_id TEXT,
  start_time TEXT,
  end_time TEXT,
  headway_secs INTEGER,
  exact_times INTEGER
);

CREATE TABLE IF NOT EXISTS shapes (
  shape_id TEXT,
  shape_pt_sequence INTEGER,
  shape_pt_lat REAL,
  shape_pt_lon REAL,
  shape_dist_traveled REAL,
  PRIMARY KEY(shape_id, shape_pt_sequence)
);

-- Materialized table to speed queries by stop + date
CREATE TABLE IF NOT EXISTS schedules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trip_id TEXT,
  service_date TEXT,
  stop_id TEXT,
  arrival_time TEXT,
  departure_time TEXT,
  stop_sequence INTEGER,
  route_id TEXT,
  route_short_name TEXT,
  feed_id INTEGER,
  UNIQUE(trip_id, service_date, stop_id, stop_sequence)
);

-- Precomputed service_day table for fast joins by date
CREATE TABLE IF NOT EXISTS service_day (
  service_id TEXT,
  service_date TEXT,
  active INTEGER DEFAULT 0,
  PRIMARY KEY(service_id, service_date)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_schedules_stop_date ON schedules(stop_id, service_date, arrival_time);
CREATE INDEX IF NOT EXISTS idx_service_day_date ON service_day(service_date);
CREATE INDEX IF NOT EXISTS idx_stop_times_stop ON stop_times(stop_id);
CREATE INDEX IF NOT EXISTS idx_trips_service ON trips(service_id);

COMMIT;
