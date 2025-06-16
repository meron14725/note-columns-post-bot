"""Logging configuration and utilities."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
from config.config import config


def setup_logger(
    name: str = "entertainment_column_system",
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    console: bool = True,
) -> logging.Logger:
    """Set up logger with file and console handlers.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        console: Whether to log to console
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Set log level
    log_level = getattr(logging, (level or config.log_level).upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    log_file_path = log_file or config.log_file_path
    if log_file_path:
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use rotating file handler to prevent log files from getting too large
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class DatabaseLogHandler(logging.Handler):
    """Custom log handler that writes to database."""
    
    def __init__(self, db_manager) -> None:
        """Initialize database log handler.
        
        Args:
            db_manager: Database manager instance
        """
        super().__init__()
        self.db_manager = db_manager
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit log record to database.
        
        Args:
            record: Log record
        """
        try:
            # Format the message
            message = self.format(record)
            
            # Extract component from logger name
            component = record.name.split('.')[-1] if '.' in record.name else record.name
            
            # Prepare details
            details = {
                'module': record.module,
                'funcName': record.funcName,
                'lineno': record.lineno,
            }
            
            # Add exception info if available
            if record.exc_info:
                details['exception'] = self.formatException(record.exc_info)
            
            # Insert into database
            query = """
                INSERT INTO system_logs (level, message, component, details)
                VALUES (?, ?, ?, ?)
            """
            self.db_manager.execute_insert(
                query, 
                (record.levelname, message, component, str(details))
            )
            
        except Exception:
            # Don't let logging errors break the application
            self.handleError(record)


# Default logger instance
default_logger = setup_logger()


def log_function_call(func):
    """Decorator to log function calls.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed with error: {e}")
            raise
    
    return wrapper


def log_execution_time(func):
    """Decorator to log function execution time.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    import time
    
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f} seconds: {e}")
            raise
    
    return wrapper