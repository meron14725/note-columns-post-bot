#!/usr/bin/env python3
"""Complete system reset script."""

import sys
import sqlite3
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.utils.database import db_manager
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)


def reset_database():
    """Reset database by dropping and recreating all tables."""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            logger.info("Dropping existing tables...")
            
            # Drop tables in correct order (respecting foreign keys)
            cursor.execute("DROP TABLE IF EXISTS twitter_posts")
            cursor.execute("DROP TABLE IF EXISTS evaluations")
            cursor.execute("DROP TABLE IF EXISTS articles")
            
            logger.info("Reading schema file...")
            schema_path = project_root / "backend/database/schema.sql"
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            logger.info("Creating tables from schema...")
            # Split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            for statement in statements:
                if statement:
                    cursor.execute(statement)
            
            conn.commit()
            logger.info("✅ Database reset completed successfully")
            
            # Verify tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            logger.info(f"Created tables: {[table[0] for table in tables]}")
            
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise


def reset_website_data():
    """Reset website JSON data files."""
    try:
        # Paths to JSON data files
        json_data_dir = project_root / "docs/data"
        output_dir = project_root / "backend/output"
        
        # Files to reset
        json_files = [
            "articles.json",
            "top5.json",
            "meta.json", 
            "categories.json",
            "statistics.json"
        ]
        
        # Empty structure for each file type
        empty_data = {
            "articles.json": {"lastUpdated": "", "total": 0, "articles": []},
            "top5.json": {"lastUpdated": "", "period": "daily", "articles": []},
            "meta.json": {"lastUpdated": "", "version": "1.0.0", "systemInfo": {}, "buildInfo": {}},
            "categories.json": {"lastUpdated": "", "categories": {}},
            "statistics.json": {"lastUpdated": "", "statistics": {}}
        }
        
        for json_file in json_files:
            for directory in [json_data_dir, output_dir]:
                file_path = directory / json_file
                if file_path.exists():
                    logger.info(f"Resetting {file_path}")
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(empty_data[json_file], f, ensure_ascii=False, indent=2)
                else:
                    logger.info(f"Creating {file_path}")
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(empty_data[json_file], f, ensure_ascii=False, indent=2)
        
        logger.info("✅ Website data reset completed successfully")
        
    except Exception as e:
        logger.error(f"Error resetting website data: {e}")
        raise


def update_config_for_main_categories():
    """Update config to focus on main 5 categories."""
    try:
        config_path = project_root / "config/urls_config.json"
        
        # Main categories to focus on
        main_categories = [
            {
                "name": "K-POP",
                "url": "https://note.com/interests/K-POP",
                "category": "K-POP"
            },
            {
                "name": "邦楽",
                "url": "https://note.com/interests/%E9%82%A6%E6%A5%BD",
                "category": "邦楽"
            },
            {
                "name": "映画",
                "url": "https://note.com/interests/%E6%98%A0%E7%94%BB",
                "category": "映画"
            },
            {
                "name": "アニメ",
                "url": "https://note.com/interests/%E3%82%A2%E3%83%8B%E3%83%A1",
                "category": "アニメ"
            },
            {
                "name": "ゲーム",
                "url": "https://note.com/interests/%E3%82%B2%E3%83%BC%E3%83%A0",
                "category": "ゲーム"
            }
        ]
        
        # Load current config
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Update with main categories only
        config["collection_urls"] = main_categories
        
        # Backup original config
        backup_path = config_path.with_suffix('.json.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info(f"Backed up original config to {backup_path}")
        
        # Save updated config
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Updated config to use {len(main_categories)} main categories")
        
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise


if __name__ == "__main__":
    logger.info("🔄 Starting complete system reset...")
    logger.info("=" * 50)
    
    try:
        logger.info("1. Resetting database...")
        reset_database()
        
        logger.info("\n2. Resetting website data...")
        reset_website_data()
        
        logger.info("\n3. Updating config for main categories...")
        update_config_for_main_categories()
        
        logger.info("\n✅ Complete system reset finished successfully!")
        logger.info("Ready for full pipeline execution.")
        
    except Exception as e:
        logger.error(f"❌ System reset failed: {e}")
        sys.exit(1)