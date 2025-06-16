"""Database connection and management utilities."""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

try:
    from config.config import config
except ImportError:
    # Fallback for when config is not available
    class MockConfig:
        database_path = "backend/database/entertainment_columns.db"
    config = MockConfig()

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and management class."""
    
    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or config.database_path
        self.ensure_database_exists()
    
    def ensure_database_exists(self) -> None:
        """Ensure database file and tables exist."""
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database with schema
        self.init_database()
    
    def init_database(self) -> None:
        """Initialize database with schema."""
        schema_path = Path(__file__).parent.parent.parent / "database" / "schema.sql"
        
        if not schema_path.exists():
            logger.error(f"Schema file not found: {schema_path}")
            return
        
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        
        with self.get_connection() as conn:
            conn.executescript(schema_sql)
            conn.commit()
            logger.info("Database initialized successfully")
    
    @contextmanager
    def get_connection(self):
        """Get database connection context manager.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of dictionaries representing rows
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or ())
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_update(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> int:
        """Execute INSERT, UPDATE, or DELETE query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or ())
            conn.commit()
            return cursor.rowcount
    
    def execute_insert(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> int:
        """Execute INSERT query and return last row ID.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Last inserted row ID
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or ())
            conn.commit()
            return cursor.lastrowid
    
    def execute_many(
        self, 
        query: str, 
        param_list: List[tuple]
    ) -> int:
        """Execute query with multiple parameter sets.
        
        Args:
            query: SQL query string
            param_list: List of parameter tuples
            
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.executemany(query, param_list)
            conn.commit()
            return cursor.rowcount
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists.
        
        Args:
            table_name: Name of the table
            
        Returns:
            True if table exists, False otherwise
        """
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        result = self.execute_query(query, (table_name,))
        return len(result) > 0
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information
        """
        query = f"PRAGMA table_info({table_name})"
        return self.execute_query(query)
    
    def backup_database(self, backup_path: str) -> None:
        """Create database backup.
        
        Args:
            backup_path: Path for backup file
        """
        backup_path_obj = Path(backup_path)
        backup_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with self.get_connection() as conn:
            with sqlite3.connect(backup_path) as backup_conn:
                conn.backup(backup_conn)
        
        logger.info(f"Database backed up to: {backup_path}")
    
    def vacuum_database(self) -> None:
        """Optimize database by running VACUUM."""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
            conn.commit()
        
        logger.info("Database vacuumed successfully")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        stats = {}
        
        # Get table counts
        tables = ['articles', 'evaluations', 'twitter_posts', 'system_logs']
        for table in tables:
            if self.table_exists(table):
                query = f"SELECT COUNT(*) as count FROM {table}"
                result = self.execute_query(query)
                stats[f"{table}_count"] = result[0]['count'] if result else 0
        
        # Get database size
        db_path = Path(self.db_path)
        if db_path.exists():
            stats['database_size_bytes'] = db_path.stat().st_size
        
        return stats


# Global database manager instance
db_manager = DatabaseManager()