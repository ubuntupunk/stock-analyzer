"""
Centralized logging configuration for the stock analyzer backend.
Provides consistent logging across all modules with proper formatting and levels.
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str,
    level: Optional[int] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Configure and return a logger instance with consistent formatting.
    
    Args:
        name: Logger name (typically __name__ from calling module)
        level: Logging level (defaults to INFO, or DEBUG if AWS_SAM_LOCAL is set)
        format_string: Custom format string (optional)
    
    Returns:
        Configured logger instance
    """
    import os
    
    # Determine log level
    if level is None:
        # Use DEBUG in local development, INFO in production
        is_local = os.environ.get('AWS_SAM_LOCAL') or os.environ.get('FLASK_ENV') == 'development'
        level = logging.DEBUG if is_local else logging.INFO
    
    # Default format with timestamp, level, module, and message
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(format_string)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger
