"""SQLite storage implementation with ACID guarantees."""

import json
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

import structlog

from property_monitor.domain.exceptions import DataCorruptedError, StorageError
from property_monitor.domain.models import Property


class SQLiteStorage:
    """Production-grade SQLite storage with atomic transactions."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        db_path: Path,
        backup_enabled: bool = True,
        backup_retention_days: int = 7,
        logger: structlog.stdlib.BoundLogger | None = None,
    ) -> None:
        """
        Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file
            backup_enabled: Enable automatic backups
            backup_retention_days: Days to retain backups
            logger: Structured logger instance
        """
        self.db_path = db_path
        self.backup_enabled = backup_enabled
        self.backup_retention_days = backup_retention_days
        self.logger = logger or structlog.get_logger(__name__)

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """
        Context manager for database connections with automatic commit/rollback.

        Yields:
            SQLite connection
        """
        conn = sqlite3.connect(
            self.db_path, isolation_level="DEFERRED", timeout=30.0
        )
        conn.row_factory = sqlite3.Row  # Dict-like access to rows
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema if not exists."""
        with self._get_connection() as conn:
            # Properties table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS properties (
                    id TEXT PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    address TEXT,
                    price INTEGER NOT NULL,
                    bedrooms INTEGER,
                    bathrooms REAL,
                    property_type TEXT,
                    posted_minutes_ago INTEGER,
                    raw_data TEXT,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    last_price INTEGER,
                    price_changed_at TEXT
                )
            """)

            # Indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_seen
                ON properties(last_seen_at)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_price
                ON properties(price)
            """)

            # Metadata table for configuration
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # Set schema version
            conn.execute(
                "INSERT OR IGNORE INTO metadata (key, value) VALUES (?, ?)",
                ("schema_version", str(self.SCHEMA_VERSION)),
            )

            # Set initialized flag (False by default)
            conn.execute(
                "INSERT OR IGNORE INTO metadata (key, value) VALUES (?, ?)",
                ("is_initialized", "false"),
            )

        self.logger.info("database_initialized", db_path=str(self.db_path))

    def is_initialized(self) -> bool:
        """
        Check if storage has been initialized with baseline data.

        Returns:
            True if initialized, False otherwise
        """
        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT value FROM metadata WHERE key = ?", ("is_initialized",)
            ).fetchone()

            return result is not None and result[0] == "true"

    def set_initialized(self) -> None:
        """Mark storage as initialized."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE metadata SET value = ? WHERE key = ?",
                ("true", "is_initialized"),
            )
            self.logger.info("storage_marked_initialized")

    def is_new_or_updated(self, property_data: Property) -> bool:
        """
        Check if property is new or has been updated (price changed).

        Args:
            property_data: Property to check

        Returns:
            True if new or price changed, False otherwise
        """
        with self._get_connection() as conn:
            existing = conn.execute(
                "SELECT price, last_seen_at FROM properties WHERE id = ?",
                (property_data.property_id,),
            ).fetchone()

            if existing is None:
                # New property
                return True

            # Check for price change
            if existing["price"] != property_data.price:
                self.logger.info(
                    "price_changed",
                    property_id=property_data.property_id,
                    old_price=existing["price"],
                    new_price=property_data.price,
                )
                return True

            # Property exists and price hasn't changed
            return False

    def save(self, property_data: Property) -> None:
        """
        Save property to storage (insert or update).

        Args:
            property_data: Property to save
        """
        with self._get_connection() as conn:
            existing = conn.execute(
                "SELECT price FROM properties WHERE id = ?", (property_data.property_id,)
            ).fetchone()

            now = datetime.utcnow().isoformat()

            if existing:
                # Update existing property
                price_changed = existing["price"] != property_data.price

                conn.execute(
                    """
                    UPDATE properties
                    SET url = ?, title = ?, address = ?, price = ?,
                        bedrooms = ?, bathrooms = ?, property_type = ?,
                        posted_minutes_ago = ?, raw_data = ?, last_seen_at = ?,
                        last_price = ?, price_changed_at = ?
                    WHERE id = ?
                """,
                    (
                        property_data.url,
                        property_data.title,
                        property_data.address,
                        property_data.price,
                        property_data.bedrooms,
                        property_data.bathrooms,
                        property_data.property_type,
                        property_data.posted_minutes_ago,
                        json.dumps(property_data.raw_data),
                        now,
                        existing["price"] if price_changed else None,
                        now if price_changed else None,
                        property_data.property_id,
                    ),
                )

                self.logger.debug(
                    "property_updated",
                    property_id=property_data.property_id,
                    price_changed=price_changed,
                )
            else:
                # Insert new property
                conn.execute(
                    """
                    INSERT INTO properties (
                        id, url, title, address, price, bedrooms, bathrooms,
                        property_type, posted_minutes_ago, raw_data,
                        first_seen_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        property_data.property_id,
                        property_data.url,
                        property_data.title,
                        property_data.address,
                        property_data.price,
                        property_data.bedrooms,
                        property_data.bathrooms,
                        property_data.property_type,
                        property_data.posted_minutes_ago,
                        json.dumps(property_data.raw_data),
                        now,
                        now,
                    ),
                )

                self.logger.debug("property_inserted", property_id=property_data.property_id)

    def get_property_count(self) -> int:
        """
        Get total number of properties in storage.

        Returns:
            Count of properties
        """
        with self._get_connection() as conn:
            result = conn.execute("SELECT COUNT(*) FROM properties").fetchone()
            return result[0] if result else 0

    def backup(self) -> Path | None:
        """
        Create a backup of the database.

        Returns:
            Path to backup file, or None if backups are disabled
        """
        if not self.backup_enabled:
            return None

        backup_dir = self.db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{self.db_path.stem}_{timestamp}.db"

        # Create backup
        shutil.copy2(self.db_path, backup_path)

        self.logger.info("backup_created", backup_path=str(backup_path))

        # Clean up old backups
        self._cleanup_old_backups(backup_dir)

        return backup_path

    def _cleanup_old_backups(self, backup_dir: Path) -> None:
        """
        Remove backups older than retention period.

        Args:
            backup_dir: Directory containing backups
        """
        cutoff = datetime.utcnow() - timedelta(days=self.backup_retention_days)

        for backup_file in backup_dir.glob("*.db"):
            if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff:
                backup_file.unlink()
                self.logger.debug("backup_deleted", backup_file=str(backup_file))
