"""
CivicSight AI Service
Central application logging.

This module provides one consistent logging configuration for the
entire application.

Security rules:
- Never log API keys.
- Never log authorization headers.
- Never log passwords or tokens.
- Avoid logging raw citizen-uploaded content.
"""

import logging
import os
import sys
from typing import Final


# ============================================================
# Constants
# ============================================================

DEFAULT_LOG_LEVEL: Final[str] = "INFO"

LOG_FORMAT: Final[str] = (
    "%(asctime)s | "
    "%(levelname)s | "
    "%(name)s | "
    "%(message)s"
)

DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


# ============================================================
# Log Level
# ============================================================

def _get_log_level() -> int:
    """
    Read the log level from the environment.

    Supported values:
    DEBUG, INFO, WARNING, ERROR, CRITICAL

    Invalid values fall back to INFO.
    """

    configured_level = os.getenv(
        "LOG_LEVEL",
        DEFAULT_LOG_LEVEL,
    ).upper()

    return getattr(
        logging,
        configured_level,
        logging.INFO,
    )


# ============================================================
# Logger Configuration
# ============================================================

def configure_logging() -> None:
    """
    Configure application-wide logging.

    This function is safe to call multiple times.
    """

    logging.basicConfig(
        level=_get_log_level(),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        stream=sys.stdout,
        force=True,
    )


# Configure logging when this module is imported.
configure_logging()


# ============================================================
# Logger Factory
# ============================================================

def get_logger(name: str) -> logging.Logger:
    """
    Return a logger for the requested module.

    Example:
        logger = get_logger(__name__)
    """

    return logging.getLogger(name)


# ============================================================
# Application Logger
# ============================================================

logger = get_logger("civicsight")