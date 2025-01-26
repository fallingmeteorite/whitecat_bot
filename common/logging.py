# -*- coding: utf-8 -*-
import sys
from loguru import logger

# Hardcoded log format for performance
DEFAULT_FORMAT: str = (
    "<g>{time:YYYY-MM-DD HH:mm:ss}</g> "
    "[<lvl>{level}</lvl>] "
    "<c><u>{name}:{line}</u></c> | "
    "{message}"
)

# Default log level
LOG_LEVEL: str = "INFO"

# Flag to check if logger is already configured
_logger_configured: bool = False

def configure_logger():
    """
    Configure the logger if not already configured.
    """
    global _logger_configured

    # Skip if logger is already configured
    if _logger_configured:
        return

    # Remove all default handlers (only if necessary)
    logger.remove()

    # Configure logger to output to console
    logger.add(
        sys.stdout,
        format=DEFAULT_FORMAT,
        level=LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True
    )

    # Mark logger as configured
    _logger_configured = True

# Initialize logger configuration at module load
configure_logger()

# Example log message (only for debugging)
# logger.info("Logger configuration completed")
