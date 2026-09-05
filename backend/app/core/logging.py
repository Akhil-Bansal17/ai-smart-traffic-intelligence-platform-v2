"""
Structured logging setup.

Uses the standard library `logging` module with a consistent format
across the app, driven by settings.log_level. No print() statements
should be used anywhere else in the backend — get a logger via
`get_logger(__name__)` instead.
"""
import logging
import sys

from app.config.settings import settings

_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    # Never let this module accidentally log secrets - a reminder, not enforcement.
    logging.getLogger("app").setLevel(level)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
