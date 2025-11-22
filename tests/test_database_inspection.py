"""Database inspection tests for development and debugging."""
import sqlite3
import os
import pytest
from app.config.settings import settings


@pytest.fixture
def db_connection():
    """Provide a database connection for tests."""
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data/gtfs", "gtfs.db")
    if not os.path.exists(db_path):
        pytest.skip(f"Database not found at {db_path}")
    
    conn = sqlite3.connect(db_path)
    yield conn
    conn.close()


def test_database_tables_exist(db_connection):
    """Verify all expected tables exist in the database."""
    cur = db_connection.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    
    expected_tables = {'stops', 'routes', 'trips', 'stop_times', 'calendar', 'agency'}
    assert set(tables) >= expected_tables, f"Missing tables: {expected_tables - set(tables)}"


def test_stops_table_has_data(db_connection):
    """Verify stops table contains data."""
    cur = db_connection.cursor()
    cur.execute("SELECT COUNT(*) FROM stops")
    count = cur.fetchone()[0]
    assert count > 0, "Stops table is empty"


def test_stop_id_format(db_connection):
    """Verify stop_id is stored as text with leading zeros preserved."""
    cur = db_connection.cursor()
    cur.execute("SELECT stop_id FROM stops WHERE stop_id LIKE '0%' LIMIT 1")
    result = cur.fetchone()
    
    if result:
        stop_id = result[0]
        assert isinstance(stop_id, str), "stop_id should be stored as text"
        assert stop_id.startswith('0'), "Leading zeros should be preserved"


def test_stops_table_schema(db_connection):
    """Verify stops table has correct schema."""
    cur = db_connection.cursor()
    cur.execute("PRAGMA table_info(stops)")
    columns = {col[1]: col[2] for col in cur.fetchall()}
    
    assert 'stop_id' in columns
    assert 'stop_name' in columns
    assert 'stop_lat' in columns
    assert 'stop_lon' in columns


def test_stop_times_has_data(db_connection):
    """Verify stop_times table contains data."""
    cur = db_connection.cursor()
    cur.execute("SELECT COUNT(*) FROM stop_times")
    count = cur.fetchone()[0]
    assert count > 0, "stop_times table is empty"


def test_trips_linked_to_routes(db_connection):
    """Verify trips are properly linked to routes."""
    cur = db_connection.cursor()
    cur.execute("""
        SELECT COUNT(*) 
        FROM trips t 
        LEFT JOIN routes r ON t.route_id = r.route_id 
        WHERE r.route_id IS NULL
    """)
    orphaned_trips = cur.fetchone()[0]
    assert orphaned_trips == 0, f"Found {orphaned_trips} trips without matching routes"


def test_calendar_has_services(db_connection):
    """Verify calendar table contains service definitions."""
    cur = db_connection.cursor()
    cur.execute("SELECT COUNT(*) FROM calendar")
    count = cur.fetchone()[0]
    assert count > 0, "calendar table is empty"


def test_sample_data_query(db_connection):
    """Test a sample query joining multiple tables."""
    cur = db_connection.cursor()
    cur.execute("""
        SELECT s.stop_name, r.route_short_name, st.arrival_time
        FROM stop_times st
        JOIN stops s ON st.stop_id = s.stop_id
        JOIN trips t ON st.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        LIMIT 5
    """)
    results = cur.fetchall()
    assert len(results) > 0, "Sample join query returned no results"
    
    # Verify structure of results
    for row in results:
        assert len(row) == 3
        assert row[0] is not None  # stop_name
        assert row[2] is not None  # arrival_time


if __name__ == "__main__":
    # Allow running directly for manual inspection
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data/gtfs", "gtfs.db")
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        exit(1)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # List tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    print(f"Tables: {tables}\n")
    
    # Check stops
    cur.execute("SELECT COUNT(*) FROM stops")
    print(f"Total stops: {cur.fetchone()[0]}")
    
    cur.execute("SELECT * FROM stops LIMIT 3")
    print("\nFirst 3 stops:")
    for row in cur.fetchall():
        print(f"  {row}")
    
    conn.close()
