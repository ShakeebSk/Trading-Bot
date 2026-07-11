"""
Centralized logging configuration.

Logs go to both:
- a rotating log file (bot.log) for permanent record of requests/responses/errors
- the console, at a higher level, so the CLI stays readable

Usage:
    from bot.logging_config import setup_logging
    logger = setup_logging()
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "bot.log"

_LOGGER_NAME = "trading_bot"
_configured = False


def setup_logging(log_level: int = logging.DEBUG) -> logging.Logger:
    """
    Configure and return the shared application logger.

    File handler: DEBUG+ (captures full request/response/error detail)
    Console handler: INFO+ (keeps terminal output clean)
    """
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)

    if _configured:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger.setLevel(log_level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _configured = True
    return logger


def get_logger() -> logging.Logger:
    """Get the shared logger, configuring it on first use."""
    if not _configured:
        return setup_logging()
    return logging.getLogger(_LOGGER_NAME)
