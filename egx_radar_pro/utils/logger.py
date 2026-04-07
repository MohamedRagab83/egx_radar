"""
utils/logger.py — EGX Radar Pro
==================================
Centralised logging factory.

Usage
-----
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("message")
"""

from __future__ import annotations

import logging
import sys


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Return a module-level logger with a consistent, timestamped format.

    Calling this multiple times with the same name is safe — handlers are
    only added once.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
