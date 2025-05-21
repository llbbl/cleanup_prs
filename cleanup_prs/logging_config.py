"""Logging configuration for the cleanup-prs tool."""

import logging
import logging.handlers
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

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

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, style: str = "%", *args: Any, **kwargs: Any):
        """Initialize the formatter with optional custom format.

        Args:
            fmt: Optional format string for JSON fields
            datefmt: Optional date format string
            style: Format style ('%', '{', or '$')
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        super().__init__(fmt, datefmt, style, *args, **kwargs)
        self._fields = self._parse_format_string(fmt) if fmt else None

    def _parse_format_string(self, fmt: str) -> List[str]:
        """Parse the format string to extract field names.

        Args:
            fmt: Format string containing field names

        Returns:
            List of field names found in the format string
        """
        if not fmt:
            return []
        return [f.strip() for f in fmt.split() if f.strip()]

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

        # If specific fields were requested, filter the log record
        if self._fields:
            filtered_record = {}
            for field in self._fields:
                if field in log_record:
                    filtered_record[field] = log_record[field]
            log_record.clear()
            log_record.update(filtered_record)


class CustomTextFormatter(logging.Formatter):
    """Custom text formatter with support for custom formats."""

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, style: str = "%"):
        """Initialize the formatter with custom format.

        Args:
            fmt: Optional format string
            datefmt: Optional date format string
            style: Format style ('%', '{', or '$')
        """
        super().__init__(fmt, datefmt, style)


def create_rotating_handler(
    log_file_path: str,
    max_bytes: Optional[int] = None,
    backup_count: int = 4,
    when: Optional[str] = None,
    interval: int = 1,
    compress: bool = True,
) -> Union[logging.handlers.RotatingFileHandler, logging.handlers.TimedRotatingFileHandler]:
    """Create a rotating file handler with the specified configuration.

    Args:
        log_file_path: Path to the log file
        max_bytes: Maximum size in bytes before rotation (for size-based rotation)
        backup_count: Number of backup files to keep
        when: When to rotate ('S', 'M', 'H', 'D', 'W0'-'W6', 'midnight')
        interval: Interval for time-based rotation
        compress: Whether to compress rotated logs

    Returns:
        Configured rotating file handler

    Raises:
        ValueError: If neither max_bytes nor when is specified
    """
    if max_bytes is not None:
        handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
    elif when is not None:
        handler = logging.handlers.TimedRotatingFileHandler(
            log_file_path,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding="utf-8",
        )
    else:
        raise ValueError("Either max_bytes or when must be specified")

    if compress and isinstance(handler, logging.handlers.TimedRotatingFileHandler):
        handler.suffix = "%Y-%m-%d.gz"
        handler.extMatch = r"^\d{4}-\d{2}-\d{2}\.gz$"
        handler.rotator = lambda source, dest: os.system(f"gzip -c {source} > {dest} && rm {source}")

    return handler


def setup_logging(
    log_file_path: str,
    log_level: int = logging.INFO,
    json_format: bool = True,
    request_id: Optional[str] = None,
    log_format: Optional[str] = None,
    max_bytes: Optional[int] = None,
    backup_count: int = 4,
    rotate_when: Optional[str] = None,
    rotate_interval: int = 1,
    compress_logs: bool = True,
) -> logging.Logger:
    """Sets up logging with JSON formatting and file rotation.

    Args:
        log_file_path: Path to the log file
        log_level: Logging level (default: INFO)
        json_format: Whether to use JSON formatting (default: True)
        request_id: Optional request ID to use (default: None, will generate one)
        log_format: Optional custom format string for logs
        max_bytes: Maximum size in bytes before rotation (for size-based rotation)
        backup_count: Number of backup files to keep
        rotate_when: When to rotate ('S', 'M', 'H', 'D', 'W0'-'W6', 'midnight')
        rotate_interval: Interval for time-based rotation
        compress_logs: Whether to compress rotated logs

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
            fmt=log_format or "%(timestamp)s %(level)s %(name)s %(module)s %(function)s %(line)s %(message)s"
        )
    else:
        formatter = CustomTextFormatter(
            fmt=log_format or "%(asctime)s | %(levelname)s | %(request_id)s | %(module)s:%(funcName)s:%(lineno)d | %(message)s"
        )

    # Add request ID filter
    request_filter = RequestIdFilter()
    if request_id:
        request_filter.request_id = request_id
    logger.addFilter(request_filter)

    # Create rotating file handler
    file_handler = create_rotating_handler(
        log_file_path,
        max_bytes=max_bytes,
        backup_count=backup_count,
        when=rotate_when,
        interval=rotate_interval,
        compress=compress_logs,
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
