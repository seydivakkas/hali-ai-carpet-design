"""Idempotent database schema migrations per spec Section 22."""

from __future__ import annotations

import sqlite3

from carpet_designer.logging_config import get_logger

logger = get_logger("persistence.migrations")

SCHEMA_VERSION = 1

_MIGRATIONS: list[str] = [
    # Version 1: Initial schema
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS recipes (
        recipe_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        recipe_json TEXT NOT NULL,
        recipe_sha256 TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS generations (
        generation_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        recipe_id TEXT REFERENCES recipes(recipe_id),
        model_id TEXT NOT NULL,
        lora_ids_json TEXT DEFAULT '[]',
        seed INTEGER NOT NULL,
        scheduler TEXT NOT NULL,
        steps INTEGER NOT NULL,
        guidance_scale REAL NOT NULL,
        width INTEGER NOT NULL,
        height INTEGER NOT NULL,
        image_sha256 TEXT NOT NULL,
        image_path TEXT NOT NULL,
        total_latency_ms REAL DEFAULT 0.0,
        status TEXT NOT NULL DEFAULT 'NOT_RUN'
    );

    CREATE TABLE IF NOT EXISTS analyses (
        analysis_id TEXT PRIMARY KEY,
        generation_id TEXT REFERENCES generations(generation_id),
        palette_id TEXT DEFAULT '',
        mean_delta_e REAL DEFAULT 0.0,
        symmetry_score REAL DEFAULT 0.0,
        seam_score REAL DEFAULT 0.0,
        repeatability_score REAL DEFAULT 0.0,
        nearest_match_id TEXT DEFAULT '',
        nearest_similarity REAL DEFAULT 0.0,
        result_json_path TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS collections (
        collection_item_id TEXT PRIMARY KEY,
        generation_id TEXT,
        source_type TEXT NOT NULL,
        source_sha256 TEXT NOT NULL,
        title TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'CANDIDATE',
        reviewer TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS reviews (
        review_id TEXT PRIMARY KEY,
        generation_id TEXT REFERENCES generations(generation_id),
        reviewer TEXT NOT NULL,
        rubric_json TEXT NOT NULL DEFAULT '{}',
        overall_preference INTEGER DEFAULT 0,
        comment TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS models (
        model_id TEXT PRIMARY KEY,
        repository_id TEXT NOT NULL,
        revision TEXT DEFAULT '',
        license TEXT DEFAULT '',
        local_path TEXT DEFAULT '',
        artifact_sha256 TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'NOT_FOUND'
    );

    CREATE TABLE IF NOT EXISTS lora_adapters (
        lora_id TEXT PRIMARY KEY,
        adapter_name TEXT NOT NULL,
        base_model_id TEXT REFERENCES models(model_id),
        training_run_id TEXT DEFAULT '',
        dataset_manifest_sha256 TEXT DEFAULT '',
        license_register_sha256 TEXT DEFAULT '',
        artifact_path TEXT DEFAULT '',
        artifact_sha256 TEXT DEFAULT '',
        rank INTEGER DEFAULT 16,
        alpha INTEGER DEFAULT 16,
        status TEXT NOT NULL DEFAULT 'DRAFT',
        metrics_path TEXT DEFAULT ''
    );
    """,
]


def run_migrations(conn: sqlite3.Connection) -> None:
    """Run all pending migrations idempotently.

    Args:
        conn: SQLite connection to migrate.
    """
    # Check current version
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        current_version = row[0] if row and row[0] is not None else 0
    except sqlite3.OperationalError:
        current_version = 0

    for version_idx, migration_sql in enumerate(_MIGRATIONS, start=1):
        if version_idx > current_version:
            logger.info(
                "Applying migration v%d",
                version_idx,
                extra={"run_id": f"migration_v{version_idx}"},
            )
            conn.executescript(migration_sql)
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (version_idx,),
            )
            conn.commit()

    logger.info("Database at schema version %d", SCHEMA_VERSION)
