"""Performance monitoring for the cleanup-prs tool.

This module provides functionality for monitoring and reporting performance metrics
such as operation timings, memory usage, and API call statistics.
"""

import functools
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""

    operation: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """Monitors and reports performance metrics."""

    def __init__(self):
        """Initialize the performance monitor."""
        self.operations: List[OperationMetrics] = []
        self._current_operation: Optional[OperationMetrics] = None

    def start_operation(self, operation: str, **details: Any) -> None:
        """Start timing an operation.

        Args:
            operation: Name of the operation
            **details: Additional details about the operation
        """
        self._current_operation = OperationMetrics(
            operation=operation,
            start_time=datetime.now(),
            details=details,
        )
        logger.debug(
            "Starting operation",
            extra={
                "operation": operation,
                "details": details,
            },
        )

    def end_operation(self, success: bool = True, error: Optional[str] = None, **details: Any) -> None:
        """End timing the current operation.

        Args:
            success: Whether the operation was successful
            error: Error message if the operation failed
            **details: Additional details about the operation
        """
        if not self._current_operation:
            logger.warning("No operation in progress")
            return

        self._current_operation.end_time = datetime.now()
        self._current_operation.duration = (
            self._current_operation.end_time - self._current_operation.start_time
        ).total_seconds()
        self._current_operation.success = success
        self._current_operation.error = error
        self._current_operation.details.update(details)

        logger.debug(
            "Completed operation",
            extra={
                "operation": self._current_operation.operation,
                "duration": self._current_operation.duration,
                "success": success,
                "error": error,
                "details": self._current_operation.details,
            },
        )

        self.operations.append(self._current_operation)
        self._current_operation = None

    def get_operation_summary(self) -> Dict[str, Any]:
        """Get a summary of all operations.

        Returns:
            Dict containing operation statistics
        """
        if not self.operations:
            return {}

        total_duration = sum(op.duration or 0 for op in self.operations)
        successful_ops = sum(1 for op in self.operations if op.success)
        failed_ops = len(self.operations) - successful_ops

        return {
            "total_operations": len(self.operations),
            "successful_operations": successful_ops,
            "failed_operations": failed_ops,
            "total_duration": total_duration,
            "average_duration": total_duration / len(self.operations) if self.operations else 0,
            "operations": [
                {
                    "operation": op.operation,
                    "duration": op.duration,
                    "success": op.success,
                    "error": op.error,
                    "details": op.details,
                }
                for op in self.operations
            ],
        }


def monitor_performance(operation: str) -> Callable:
    """Decorator to monitor the performance of a function.

    Args:
        operation: Name of the operation to monitor

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            monitor = PerformanceMonitor()
            monitor.start_operation(operation, args=args, kwargs=kwargs)
            try:
                result = func(*args, **kwargs)
                monitor.end_operation(success=True, result=result)
                return result
            except Exception as e:
                monitor.end_operation(success=False, error=str(e))
                raise

        return wrapper

    return decorator


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance.

    Returns:
        PerformanceMonitor instance
    """
    return _performance_monitor 