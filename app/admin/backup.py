"""Database backup via SQLite's VACUUM INTO.

VACUUM INTO writes a clean, consistent copy of the database to a new file. It is
safe to run while the app is open because it reads a consistent snapshot. This is
maintenance SQL (no ORM equivalent); the target path is passed as a bound
parameter, never string-interpolated.
"""

import os
import sqlite3
from datetime import datetime


def backup_filename(now: datetime) -> str:
    """Timestamped backup filename, e.g. finance-20260630-142501.db."""
    return f"finance-{now.strftime('%Y%m%d-%H%M%S')}.db"


def create_backup(source_db_path: str, backups_dir: str, now: datetime) -> str:
    """Create a clean copy of the SQLite DB and return the backup file path.

    Creates `backups_dir` if needed. Uses a separate connection in autocommit
    mode (VACUUM cannot run inside a transaction).
    """
    os.makedirs(backups_dir, exist_ok=True)
    target = os.path.join(backups_dir, backup_filename(now))

    connection = sqlite3.connect(source_db_path)
    try:
        connection.isolation_level = None  # autocommit; VACUUM forbids transactions
        connection.execute("VACUUM INTO ?", (target,))
    finally:
        connection.close()
    return target
