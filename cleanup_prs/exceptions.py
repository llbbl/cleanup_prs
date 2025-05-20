"""Custom exceptions and error handling utilities for the cleanup-prs tool."""

import functools
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, TypeVar, cast
import logging

T = TypeVar('T')

@dataclass
class ErrorContext:
    """Context information for errors."""
    timestamp: datetime
    operation: str
    details: Dict[str, Any]
    retry_count: int = 0

class CleanupError(Exception):
    """Base exception for all cleanup-related errors."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        self.message = message
        self.context = context
        super().__init__(message)

class KubernetesError(CleanupError):
    """Exception raised for Kubernetes-related errors."""
    pass

class ContextNotFoundError(KubernetesError):
    """Exception raised when a Kubernetes context is not found."""
    pass

class NamespaceError(KubernetesError):
    """Errors related to namespace operations."""
    pass

class HelmError(CleanupError):
    """Exception raised for Helm-related errors."""
    pass

class HelmReleaseNotFoundError(HelmError):
    """Raised when a Helm release is not found."""
    pass

class HelmUninstallError(HelmError):
    """Exception raised when Helm uninstall operation fails."""
    pass

class ConfigurationError(CleanupError):
    """Errors related to configuration."""
    pass

class ValidationError(ConfigurationError):
    """Raised when configuration validation fails."""
    pass

def with_retry(max_retries: int = 3, delay: float = 1.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that adds retry logic to a function.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay)
            raise last_exception
        return cast(Callable[..., T], wrapper)
    return decorator

def handle_error(error: Exception, logger: logging.Logger) -> None:
    """Centralized error handling function.
    
    Args:
        error: The exception to handle
        logger: Logger instance to use
    """
    if isinstance(error, CleanupError):
        context = error.context
        logger.error(
            f"Error during {context.operation}: {str(error)}",
            extra={
                "error_type": error.__class__.__name__,
                "timestamp": context.timestamp.isoformat(),
                "details": context.details,
                "retry_count": context.retry_count
            }
        )
    else:
        logger.error(f"Unexpected error: {str(error)}", exc_info=True) 