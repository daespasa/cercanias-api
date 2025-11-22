import os
import sqlite3
from typing import Dict

import pandas as pd


def build_sqlite_from_dict(tables: Dict[str, pd.DataFrame], db_tmp_path: str) -> None:
    """Build a comprehensive SQLite DB file from a dict of DataFrames and write to db_tmp_path.

    This creates tables with proper schema, foreign keys, and comprehensive indexes
    for optimal query performance. The caller should atomically replace the final DB file.
    """
    import logging
    logger = logging.getLogger("cercanias")
    
    conn = sqlite3.connect(db_tmp_path)
    cur = conn.cursor()
    
    # Enable foreign keys and set performance pragmas
    try:
        cur.execute("PRAGMA foreign_keys=ON;")
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA temp_store=MEMORY;")
        cur.execute("PRAGMA cache_size=-64000;")  # 64MB cache
        cur.execute("PRAGMA mmap_size=268435456;")  # 256MB memory-mapped I/O
    except Exception as e:
        logger.warning(f"Could not set all pragmas: {e}")

    # Order matters for foreign key relationships
    table_order = [
        'agency', 'routes', 'calendar', 'calendar_dates', 
        'stops', 'shapes', 'trips', 'stop_times', 'transfers'
    ]
    
    for name in table_order:
        if name not in tables:
            logger.info(f"Skipping table {name} (not in source data)")
            continue
            
        df = tables[name]
        table_name = name
        logger.info(f"Creating table {table_name} with {len(df)} rows")
        
        try:
            # Ensure column names are safe strings
            df.columns = [str(c) for c in df.columns]
            
            # Let pandas create the table first
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            logger.info(f"Successfully created table {table_name}")
            
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            try:
                cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (dummy INTEGER);")
            except Exception:
                pass

    # Now create comprehensive indexes after all tables are loaded
    logger.info("Creating indexes...")
    
    indexes = [
        # Agency indexes
        ("ix_agency_id", "agency", "agency_id"),
        
        # Routes indexes
        ("ix_routes_route_id", "routes", "route_id"),
        ("ix_routes_agency_id", "routes", "agency_id"),
        ("ix_routes_route_type", "routes", "route_type"),
        
        # Calendar indexes
        ("ix_calendar_service_id", "calendar", "service_id"),
        ("ix_calendar_dates", "calendar", "start_date, end_date"),
        
        # Calendar dates indexes
        ("ix_calendar_dates_service_id", "calendar_dates", "service_id"),
        ("ix_calendar_dates_date", "calendar_dates", "date"),
        
        # Stops indexes (critical for performance)
        ("ix_stops_stop_id", "stops", "stop_id"),
        ("ix_stops_parent_station", "stops", "parent_station"),
        ("ix_stops_location_type", "stops", "location_type"),
        ("ix_stops_zone_id", "stops", "zone_id"),
        # Spatial index for lat/lon searches
        ("ix_stops_location", "stops", "stop_lat, stop_lon"),
        
        # Shapes indexes
        ("ix_shapes_shape_id", "shapes", "shape_id"),
        ("ix_shapes_sequence", "shapes", "shape_id, shape_pt_sequence"),
        
        # Trips indexes (critical for joins)
        ("ix_trips_trip_id", "trips", "trip_id"),
        ("ix_trips_route_id", "trips", "route_id"),
        ("ix_trips_service_id", "trips", "service_id"),
        ("ix_trips_shape_id", "trips", "shape_id"),
        ("ix_trips_direction", "trips", "direction_id"),
        
        # Stop times indexes (most critical - largest table)
        ("ix_stop_times_trip_id", "stop_times", "trip_id"),
        ("ix_stop_times_stop_id", "stop_times", "stop_id"),
        ("ix_stop_times_sequence", "stop_times", "stop_sequence"),
        # Composite indexes for common queries
        ("ix_stop_times_stop_trip", "stop_times", "stop_id, trip_id"),
        ("ix_stop_times_trip_sequence", "stop_times", "trip_id, stop_sequence"),
        ("ix_stop_times_arrival", "stop_times", "arrival_time"),
        ("ix_stop_times_departure", "stop_times", "departure_time"),
        
        # Transfers indexes
        ("ix_transfers_from_stop", "transfers", "from_stop_id"),
        ("ix_transfers_to_stop", "transfers", "to_stop_id"),
        ("ix_transfers_type", "transfers", "transfer_type"),
    ]
    
    for index_name, table_name, columns in indexes:
        try:
            # Check if table exists first
            cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            if cur.fetchone():
                cur.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns});")
                logger.debug(f"Created index {index_name} on {table_name}({columns})")
        except Exception as e:
            logger.warning(f"Could not create index {index_name}: {e}")

    # Create useful views for common queries
    logger.info("Creating views...")
    
    views = []
    
    # View: Active services today
    views.append((
        "active_services_today",
        """
        CREATE VIEW IF NOT EXISTS active_services_today AS
        SELECT DISTINCT service_id
        FROM calendar
        WHERE date('now', 'localtime') BETWEEN date(start_date) AND date(end_date)
        AND CASE CAST(strftime('%w', 'now', 'localtime') AS INTEGER)
            WHEN 0 THEN sunday = 1
            WHEN 1 THEN monday = 1
            WHEN 2 THEN tuesday = 1
            WHEN 3 THEN wednesday = 1
            WHEN 4 THEN thursday = 1
            WHEN 5 THEN friday = 1
            WHEN 6 THEN saturday = 1
        END;
        """
    ))
    
    # View: Stop details with parent station info
    views.append((
        "stops_with_parents",
        """
        CREATE VIEW IF NOT EXISTS stops_with_parents AS
        SELECT 
            s.*,
            p.stop_name as parent_station_name,
            p.stop_lat as parent_station_lat,
            p.stop_lon as parent_station_lon
        FROM stops s
        LEFT JOIN stops p ON s.parent_station = p.stop_id
        WHERE s.parent_station IS NOT NULL OR s.location_type = 0;
        """
    ))
    
    # View: Routes with agency info
    views.append((
        "routes_with_agency",
        """
        CREATE VIEW IF NOT EXISTS routes_with_agency AS
        SELECT 
            r.*,
            a.agency_name,
            a.agency_url,
            a.agency_timezone
        FROM routes r
        LEFT JOIN agency a ON r.agency_id = a.agency_id;
        """
    ))
    
    # View: Trip details with route and service
    views.append((
        "trips_detailed",
        """
        CREATE VIEW IF NOT EXISTS trips_detailed AS
        SELECT 
            t.*,
            r.route_short_name,
            r.route_long_name,
            r.route_type,
            r.route_color
        FROM trips t
        JOIN routes r ON t.route_id = r.route_id;
        """
    ))
    
    for view_name, view_sql in views:
        try:
            cur.execute(view_sql)
            logger.debug(f"Created view {view_name}")
        except Exception as e:
            logger.warning(f"Could not create view {view_name}: {e}")

    # Analyze tables for query optimizer
    logger.info("Analyzing tables for query optimization...")
    try:
        cur.execute("ANALYZE;")
    except Exception as e:
        logger.warning(f"Could not analyze tables: {e}")

    conn.commit()
    conn.close()
    logger.info("Database build complete")


def build_sqlite_from_zip(zip_path: str, db_tmp_path: str):
    """Convenience: read GTFS ZIP via existing loader and build a SQLite DB tmp file."""
    from app.core.load_gtfs import load_gtfs_from_zip

    tables = load_gtfs_from_zip(zip_path)
    build_sqlite_from_dict(tables, db_tmp_path)


def build_sqlite_from_directory(dir_path: str, db_tmp_path: str):
    """Convenience: read GTFS directory via existing loader and build a SQLite DB tmp file."""
    from app.core.load_gtfs import load_gtfs_from_directory

    tables = load_gtfs_from_directory(dir_path)
    build_sqlite_from_dict(tables, db_tmp_path)
