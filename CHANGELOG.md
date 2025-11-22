# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to Semantic Versioning.

## [Unreleased]

- Added normalized SQLite schema (`schema_v2.sql`) with `schedules` and `service_day` materialization.
- Added `gtfs_sqlite_migrator.py` to build and incrementally ingest pandas snapshots into the SQLite DB.
- Added incremental ingestion support for pandas snapshots (parquet/pkl/csv) with atomic DB swap.
- Added `GTFSStore.get_schedule_by_stop_date()` for fast schedule queries by stop+date.
- Ensured tests remain green and added documentation to `README.md` describing migration and ingest usage.

## [0.1.0] - 2025-11-22

- Initial public features: FastAPI endpoints for stops, routes and schedules; GTFS loader; test suite.
