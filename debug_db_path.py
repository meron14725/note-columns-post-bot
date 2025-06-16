#!/usr/bin/env python3
"""Debug database path and connection."""

import sys
from pathlib import Path

# Import modules using installed package structure

from backend.app.utils.database import db_manager
from backend.app.utils.logger import get_logger
import sqlite3

logger = get_logger(__name__)

def test_db_connection():
    """Test database connection and path."""
    print(f"Database path: {db_manager.db_path}")
    print(f"Database exists: {Path(db_manager.db_path).exists()}")
    
    # Test direct sqlite connection
    try:
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM article_references WHERE is_processed = 0")
        count = cursor.fetchone()[0]
        print(f"Direct SQLite query: {count} unprocessed references")
        conn.close()
    except Exception as e:
        print(f"Direct SQLite error: {e}")
    
    # Test through db_manager
    try:
        result = db_manager.execute_query("SELECT COUNT(*) FROM article_references WHERE is_processed = 0")
        print(f"db_manager query result: {result}")
        if result:
            print(f"db_manager count: {result[0][0]}")
    except Exception as e:
        print(f"db_manager error: {e}")
        logger.error(f"Database manager error: {e}")

if __name__ == "__main__":
    test_db_connection()