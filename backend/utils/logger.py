"""
Logging utility with structured logging support
"""
import logging
import sys
from typing import Optional
from datetime import datetime


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Get or create a logger with consistent formatting
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level
        log_file: Optional file path for file logging
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


class JobContextAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds job context to all log messages
    """
    
    def process(self, msg, kwargs):
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs


def get_job_logger(job_id: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a logger with job context
    
    Args:
        job_id: Unique job identifier
        level: Logging level
        
    Returns:
        Logger with job context
    """
    logger = get_logger(f"job.{job_id}", level)
    return JobContextAdapter(logger, {'job_id': job_id})
