"""Logging configuration for the cleanup-prs tool."""

import logging
import logging.handlers
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger


class RequestIdFilter(logging.Filter):
    """Adds a request ID to log records."""

    def __init__(self):
        super().__init__()
        self.request_id = str(uuid.uuid4())

    def filter(self, record):
        record.request_id = self.request_id
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.utcnow().isoformat()

        # Add log level
        log_record["level"] = record.levelname

        # Add module and function information
        log_record["module"] = record.module
        log_record["function"] = record.funcName

        # Add line number
        log_record["line"] = record.lineno

        # Add process and thread information
        log_record["process"] = record.process
        log_record["thread"] = record.thread

        # Add any extra fields from the record
        if hasattr(record, "extra"):
            log_record.update(record.extra)


def setup_logging(
    log_file_path: str,
    log_level: int = logging.INFO,
    json_format: bool = True,
    request_id: Optional[str] = None,
) -> logging.Logger:
    """Sets up logging with JSON formatting and file rotation.

    Args:
        log_file_path: Path to the log file
        log_level: Logging level (default: INFO)
        json_format: Whether to use JSON formatting (default: True)
        request_id: Optional request ID to use (default: None, will generate one)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(log_file_path)
    os.makedirs(log_dir, exist_ok=True)

    # Create formatter
    if json_format:
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(module)s %(function)s " "%(line)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(request_id)s | " "%(module)s:%(funcName)s:%(lineno)d | %(message)s"
        )

    # Add request ID filter
    request_filter = RequestIdFilter()
    if request_id:
        request_filter.request_id = request_id
    logger.addFilter(request_filter)

    # File handler with weekly rotation
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file_path,
        when="W0",  # Rotate weekly on Monday
        interval=1,
        backupCount=4,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    Args:
        name: Name of the logger

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
