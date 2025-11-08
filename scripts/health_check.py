#!/usr/bin/env python3
"""Health check script for monitoring system status."""

import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def check_health(data_dir: Path = Path("./data")) -> bool:
    """
    Check if the property monitor is healthy.

    Args:
        data_dir: Path to data directory

    Returns:
        True if healthy, False otherwise
    """
    db_path = data_dir / "properties.db"

    # Check if database exists
    if not db_path.exists():
        print("❌ ERROR: Database not found")
        return False

    try:
        # Connect to database
        conn = sqlite3.connect(db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row

        # Check if initialized
        result = conn.execute(
            "SELECT value FROM metadata WHERE key = 'is_initialized'"
        ).fetchone()

        if not result or result[0] != "true":
            print("⚠️ WARNING: Monitor not yet initialized (first run pending)")
            conn.close()
            return True  # Not an error, just not initialized yet

        # Check property count
        count_result = conn.execute("SELECT COUNT(*) as count FROM properties").fetchone()
        property_count = count_result["count"] if count_result else 0

        if property_count == 0:
            print("⚠️ WARNING: No properties in database")
            conn.close()
            return False

        # Check most recent property
        recent_result = conn.execute(
            "SELECT last_seen_at FROM properties ORDER BY last_seen_at DESC LIMIT 1"
        ).fetchone()

        if recent_result:
            last_seen = datetime.fromisoformat(recent_result["last_seen_at"])
            age = datetime.utcnow() - last_seen

            # Alert if no updates in last 2 hours (should run every 15 min)
            if age > timedelta(hours=2):
                print(
                    f"⚠️ WARNING: Last property update was {age.total_seconds() / 3600:.1f} hours ago"
                )
                print("   Monitor may not be running or may be encountering errors")
                conn.close()
                return False

        conn.close()

        # All checks passed
        print(f"✅ OK: Property monitor is healthy")
        print(f"   Properties tracked: {property_count}")
        if recent_result:
            print(f"   Last update: {age.total_seconds() / 60:.0f} minutes ago")

        return True

    except sqlite3.Error as e:
        print(f"❌ ERROR: Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: Unexpected error: {e}")
        return False


if __name__ == "__main__":
    # Allow custom data directory as argument
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./data")

    healthy = check_health(data_dir)
    sys.exit(0 if healthy else 1)
