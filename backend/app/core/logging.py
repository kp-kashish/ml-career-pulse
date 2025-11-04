"""
Logging configuration for the application
"""

import sys
from loguru import logger
from app.core.config import settings


def setup_logging():
    """
    Configure logging for the application
    """
    # Remove default handler
    logger.remove()
    
    # Add console handler with custom format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=True
    )
    
    # Add file handler for production
    if settings.ENVIRONMENT == "production":
        logger.add(
            "logs/app_{time:YYYY-MM-DD}.log",
            format=log_format,
            level=settings.LOG_LEVEL,
            rotation="00:00",
            retention="30 days",
            compression="zip"
        )
    
    return logger


# Initialize logger
log = setup_logging()