"""Structured logging configuration"""

import structlog
import logging
from typing import Any

def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured logging"""
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.iso_timestamps(),
            structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> Any:
    """Get a structured logger instance"""
    return structlog.get_logger(name)