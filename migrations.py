"""Database schema versioning and safe migrations for RentTrack.

Rules:
- The current database schema is version 1.
- Existing data is never rebuilt or overwritten by the migration runner.
- Before an actual schema change, a timestamped backup is created.
- Each future version must have an explicit migration function.
- Migrations run inside a SQLite transaction and are rolled back on error.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


CURRENT_SCHEMA_VERSION = 1
MAX_BACKUPS = 10


def _schema_info_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = 'schema_info'
        LIMIT 1
        """
    ).fetchone()
    return row is not None


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the stored schema version without changing the database."""
    if not _schema_info_exists(conn):
        return 0

    row = conn.execute(
        "SELECT version FROM schema_info WHERE id = 1"
    ).fetchone()

    if row is None:
        return 0

    return int(row[0])


def _create_schema_info(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_info (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL
        )
        """
    )


def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    _create_schema_info(conn)
    conn.execute(
        """
        INSERT INTO schema_info (id, version)
        VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET version = excluded.version
        """,
        (version,),
    )


def backup_database(db_path: Path) -> Path | None:
    """Create a timestamped copy of an existing database before migration."""
    db_path = Path(db_path)

    if not db_path.exists():
        return None

    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"rental_before_migration_{timestamp}.db"

    # Avoid overwriting a backup if two operations happen within one second.
    counter = 1
    while backup_path.exists():
        backup_path = backup_dir / (
            f"rental_before_migration_{timestamp}_{counter}.db"
        )
        counter += 1

    shutil.copy2(db_path, backup_path)
    _trim_old_backups(backup_dir)
    return backup_path


def _trim_old_backups(backup_dir: Path) -> None:
    backups = sorted(
        backup_dir.glob("rental_before_migration_*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    for old_backup in backups[MAX_BACKUPS:]:
        try:
            old_backup.unlink()
        except OSError:
            # A backup that cannot be removed should not stop the application.
            pass


def _integrity_check(conn: sqlite3.Connection) -> None:
    row = conn.execute("PRAGMA integrity_check").fetchone()
    result = row[0] if row else None
    if result != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {result}")


# ---------------------------------------------------------------------------
# Future migration examples
# ---------------------------------------------------------------------------
#
# def migrate_v1_to_v2(conn):
#     conn.execute("ALTER TABLE ...")
#
# Then add:
#     2: migrate_v1_to_v2
#
# Do NOT edit old migration functions after a release. Add a new version
# instead, so databases can be upgraded in a predictable sequence.
# ---------------------------------------------------------------------------


MIGRATIONS = {
    # 2: migrate_v1_to_v2,
}


def migrate_database(conn: sqlite3.Connection, db_path: Path) -> Path | None:
    """Initialize or upgrade the RentTrack schema safely.

    Returns the path of the backup created before a migration, or None when
    no backup was necessary.
    """
    current_version = get_schema_version(conn)

    if current_version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            "This RentTrack version cannot open the database because the "
            f"database schema is newer (v{current_version}) than this app "
            f"supports (v{CURRENT_SCHEMA_VERSION}). Please update RentTrack."
        )

    # A database created by the current application before schema versioning
    # existed is treated as the v1 baseline. No business tables are changed.
    if current_version == 0 and not _schema_info_exists(conn):
        backup_path = backup_database(db_path)
        conn.execute("BEGIN IMMEDIATE")
        try:
            set_schema_version(conn, CURRENT_SCHEMA_VERSION)
            _integrity_check(conn)
            conn.commit()
            return backup_path
        except Exception:
            conn.rollback()
            raise

    if current_version == CURRENT_SCHEMA_VERSION:
        return None

    backup_path = backup_database(db_path)

    conn.execute("BEGIN IMMEDIATE")
    try:
        for target_version in range(current_version + 1, CURRENT_SCHEMA_VERSION + 1):
            migration = MIGRATIONS.get(target_version)
            if migration is None:
                raise RuntimeError(
                    f"No migration is defined for database schema v{target_version}."
                )

            migration(conn)
            set_schema_version(conn, target_version)

        _integrity_check(conn)
        conn.commit()
        return backup_path

    except Exception:
        conn.rollback()
        raise
