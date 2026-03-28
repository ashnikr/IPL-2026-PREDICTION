"""Logging setup using loguru."""

import sys
from loguru import logger
from config.settings import settings

# Remove default handler
logger.remove()

# Console handler
logger.add(
    sys.stderr,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
)

# File handler
logger.add(
    settings.log_dir / "ipl_system.log",
    rotation="10 MB",
    retention="30 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
)

__all__ = ["logger"]
