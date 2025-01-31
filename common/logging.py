# -*- coding: utf-8 -*-
import sys
import os
from loguru import logger
from datetime import datetime

# Hardcoded log format for performance
DEFAULT_FORMAT: str = (
    "<g>{time:YYYY-MM-DD HH:mm:ss}</g> "
    "[<lvl>{level}</lvl>] "
    "<c><u>{name}:{line}</u></c>> "
    "{message}"
)

# Default log level
LOG_LEVEL: str = "DEBUG"

# Flag to check if logger is already configured
_logger_configured: bool = False

def ensure_log_file_exists(log_file: str):
    """
    Ensure the log file exists, create it if necessary.
    :param log_file: Path to the log file
    """
    if not os.path.exists(log_file):
        with open(log_file, 'w'):
            logger.info(f"Log file created: {log_file}")

def configure_logger(log_directory: str):
    """
    Configure the logger if not already configured.
    :param log_directory: Directory to store log files
    """
    global _logger_configured

    # Skip if logger is already configured
    if _logger_configured:
        return

    # Ensure the log directory exists
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
        logger.info(f"Created log directory: {log_directory}")

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

    # Configure logger to output to a file with today's date as the filename
    log_file = datetime.now().strftime(f"{log_directory}/%Y-%m-%d.log")  # Format: log_directory/YYYY-MM-DD.log
    logger.add(
        log_file,
        format=DEFAULT_FORMAT,
        level=LOG_LEVEL,
        backtrace=True,
        diagnose=True,
        rotation="00:00",  # Rotate logs at midnight
        enqueue=True,  # Ensure thread-safe logging
        retention="7 days",  # Keep logs for 7 days
        compression="zip"  # Optional: compress old log files
    )

    # Mark logger as configured
    _logger_configured = True

# Function to write log messages
def write_log_message(message: str):
    """
    Write a log message to the configured log file.
    :param message: Message to log
    """
    log_file = datetime.now().strftime(f"{log_directory}/%Y-%m-%d.log")
    ensure_log_file_exists(log_file)
    logger.info(message)


