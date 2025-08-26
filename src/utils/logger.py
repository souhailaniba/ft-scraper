"""
Logging utilities for FT Scraper
"""

import logging
import logging.handlers
from pathlib import Path
from config.settings import LOG_FORMAT, LOG_LEVEL, LOG_FILE_MAX_SIZE, LOG_BACKUP_COUNT, LOGS_DIR


class Logger:
    """Logger utility class for consistent logging across the application"""
    
    def __init__(self, name: str, log_file: str = None):
        """
        Initialize logger
        
        Args:
            name: Logger name (usually __name__)
            log_file: Optional specific log file name
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, LOG_LEVEL))
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers(log_file)
    
    def _setup_handlers(self, log_file: str = None):
        """Setup file and console handlers"""
        
        # Create formatter
        formatter = logging.Formatter(LOG_FORMAT)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            log_path = LOGS_DIR / log_file
        else:
            log_path = LOGS_DIR / 'ft_scraper.log'
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=LOG_FILE_MAX_SIZE,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def critical(self, message: str):
        """Log critical message"""
        self.logger.critical(message)


def get_logger(name: str, log_file: str = None) -> Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name
        log_file: Optional log file name
    
    Returns:
        Logger instance
    """
    return Logger(name, log_file)