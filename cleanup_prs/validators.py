"""Input validation for the cleanup-prs tool.

This module provides validation functions for all user inputs to ensure
data integrity and security. It validates:
- Kubernetes context names
- Namespace names
- Release name prefixes
- Age thresholds
- File paths
- Log formats
- Rotation settings
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Union

from .exceptions import CleanupError, ErrorContext
from .logging_config import get_logger

logger = get_logger(__name__)

# Validation patterns
KUBERNETES_NAME_PATTERN = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$")
KUBERNETES_NAME_MAX_LENGTH = 253
RELEASE_PREFIX_PATTERN = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
RELEASE_PREFIX_MAX_LENGTH = 63


class ValidationError(CleanupError):
    """Exception raised for validation errors."""

    pass


def validate_kubernetes_name(name: str, field_name: str) -> None:
    """Validate a Kubernetes resource name.

    Args:
        name: Name to validate
        field_name: Name of the field being validated (for error messages)

    Raises:
        ValidationError: If the name is invalid
    """
    if not name:
        raise ValidationError(
            f"{field_name} cannot be empty",
            ErrorContext(
                operation="validate_kubernetes_name",
                details={"field": field_name, "value": name},
            ),
        )

    if len(name) > KUBERNETES_NAME_MAX_LENGTH:
        raise ValidationError(
            f"{field_name} exceeds maximum length of {KUBERNETES_NAME_MAX_LENGTH} characters",
            ErrorContext(
                operation="validate_kubernetes_name",
                details={"field": field_name, "value": name, "length": len(name)},
            ),
        )

    if not KUBERNETES_NAME_PATTERN.match(name):
        raise ValidationError(
            f"{field_name} contains invalid characters. Must be lowercase alphanumeric characters, '-', or '.', "
            "and must start and end with an alphanumeric character",
            ErrorContext(
                operation="validate_kubernetes_name",
                details={"field": field_name, "value": name},
            ),
        )


def validate_release_prefix(prefix: str) -> None:
    """Validate a Helm release name prefix.

    Args:
        prefix: Prefix to validate

    Raises:
        ValidationError: If the prefix is invalid
    """
    if not prefix:
        raise ValidationError(
            "Release prefix cannot be empty",
            ErrorContext(
                operation="validate_release_prefix",
                details={"value": prefix},
            ),
        )

    if len(prefix) > RELEASE_PREFIX_MAX_LENGTH:
        raise ValidationError(
            f"Release prefix exceeds maximum length of {RELEASE_PREFIX_MAX_LENGTH} characters",
            ErrorContext(
                operation="validate_release_prefix",
                details={"value": prefix, "length": len(prefix)},
            ),
        )

    if not RELEASE_PREFIX_PATTERN.match(prefix):
        raise ValidationError(
            "Release prefix contains invalid characters. Must be lowercase alphanumeric characters or '-', "
            "and must start and end with an alphanumeric character",
            ErrorContext(
                operation="validate_release_prefix",
                details={"value": prefix},
            ),
        )


def validate_age_threshold(days: int) -> None:
    """Validate the age threshold for releases.

    Args:
        days: Number of days to validate

    Raises:
        ValidationError: If the age threshold is invalid
    """
    if not isinstance(days, int):
        raise ValidationError(
            "Age threshold must be an integer",
            ErrorContext(
                operation="validate_age_threshold",
                details={"value": days, "type": type(days)},
            ),
        )

    if days < 0:
        raise ValidationError(
            "Age threshold cannot be negative",
            ErrorContext(
                operation="validate_age_threshold",
                details={"value": days},
            ),
        )

    if days > 3650:  # 10 years
        raise ValidationError(
            "Age threshold cannot exceed 3650 days (10 years)",
            ErrorContext(
                operation="validate_age_threshold",
                details={"value": days},
            ),
        )


def validate_file_path(path: str, must_exist: bool = False, must_be_file: bool = False) -> None:
    """Validate a file path.

    Args:
        path: Path to validate
        must_exist: Whether the path must exist
        must_be_file: Whether the path must be a file

    Raises:
        ValidationError: If the path is invalid
    """
    if not path:
        raise ValidationError(
            "File path cannot be empty",
            ErrorContext(
                operation="validate_file_path",
                details={"value": path},
            ),
        )

    try:
        path_obj = Path(path)
    except Exception as e:
        raise ValidationError(
            f"Invalid file path: {path}",
            ErrorContext(
                operation="validate_file_path",
                details={"value": path},
            ),
        ) from e

    if must_exist and not path_obj.exists():
        raise ValidationError(
            f"File does not exist: {path}",
            ErrorContext(
                operation="validate_file_path",
                details={"value": path},
            ),
        )

    if must_be_file and not path_obj.is_file():
        raise ValidationError(
            f"Path is not a file: {path}",
            ErrorContext(
                operation="validate_file_path",
                details={"value": path},
            ),
        )


def validate_log_format(format_str: str, json_format: bool = False) -> None:
    """Validate a log format string.

    Args:
        format_str: Format string to validate
        json_format: Whether the format is for JSON logging

    Raises:
        ValidationError: If the format string is invalid
    """
    if not format_str:
        raise ValidationError(
            "Log format cannot be empty",
            ErrorContext(
                operation="validate_log_format",
                details={"value": format_str, "json_format": json_format},
            ),
        )

    if json_format:
        # For JSON format, validate field names
        fields = format_str.split()
        valid_fields = {
            "timestamp",
            "level",
            "message",
            "function",
            "line",
            "module",
            "pathname",
            "process",
            "thread",
            "request_id",
        }
        invalid_fields = [f for f in fields if f not in valid_fields]
        if invalid_fields:
            raise ValidationError(
                f"Invalid JSON log fields: {', '.join(invalid_fields)}",
                ErrorContext(
                    operation="validate_log_format",
                    details={
                        "value": format_str,
                        "json_format": json_format,
                        "invalid_fields": invalid_fields,
                    },
                ),
            )
    else:
        # For text format, validate Python logging format string
        try:
            format_str % {"asctime": "", "levelname": "", "message": ""}
        except Exception as e:
            raise ValidationError(
                f"Invalid log format string: {format_str}",
                ErrorContext(
                    operation="validate_log_format",
                    details={"value": format_str, "json_format": json_format},
                ),
            ) from e


def validate_rotation_settings(
    max_bytes: Optional[int] = None,
    backup_count: Optional[int] = None,
    rotate_when: Optional[str] = None,
    rotate_interval: Optional[int] = None,
) -> None:
    """Validate log rotation settings.

    Args:
        max_bytes: Maximum log file size in bytes
        backup_count: Number of backup files to keep
        rotate_when: When to rotate logs
        rotate_interval: Interval for time-based rotation

    Raises:
        ValidationError: If any rotation setting is invalid
    """
    if max_bytes is not None:
        if not isinstance(max_bytes, int):
            raise ValidationError(
                "Maximum log size must be an integer",
                ErrorContext(
                    operation="validate_rotation_settings",
                    details={"value": max_bytes, "type": type(max_bytes)},
                ),
            )
        if max_bytes < 1024:  # 1KB
            raise ValidationError(
                "Maximum log size must be at least 1KB",
                ErrorContext(
                    operation="validate_rotation_settings",
                    details={"value": max_bytes},
                ),
            )

    if backup_count is not None:
        if not isinstance(backup_count, int):
            raise ValidationError(
                "Backup count must be an integer",
                ErrorContext(
                    operation="validate_rotation_settings",
                    details={"value": backup_count, "type": type(backup_count)},
                ),
            )
        if backup_count < 0:
            raise ValidationError(
                "Backup count cannot be negative",
                ErrorContext(
                    operation="validate_rotation_settings",
                    details={"value": backup_count},
                ),
            )

    if rotate_when is not None:
        valid_when = {"S", "M", "H", "D", "W0", "W1", "W2", "W3", "W4", "W5", "W6", "midnight"}
        if rotate_when not in valid_when:
            raise ValidationError(
                f"Invalid rotation interval: {rotate_when}. Must be one of: {', '.join(valid_when)}",
                ErrorContext(
                    operation="validate_rotation_settings",
                    details={"value": rotate_when},
                ),
            )

    if rotate_interval is not None:
        if not isinstance(rotate_interval, int):
            raise ValidationError(
                "Rotation interval must be an integer",
                ErrorContext(
                    operation="validate_rotation_settings",
                    details={"value": rotate_interval, "type": type(rotate_interval)},
                ),
            )
        if rotate_interval < 1:
            raise ValidationError(
                "Rotation interval must be at least 1",
                ErrorContext(
                    operation="validate_rotation_settings",
                    details={"value": rotate_interval},
                ),
            ) 