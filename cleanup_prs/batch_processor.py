"""Batch processing for Helm releases.

This module provides functionality for efficiently processing large numbers of Helm releases
in batches to optimize memory usage and performance.
"""

import concurrent.futures
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from .exceptions import CleanupError, ErrorContext
from .logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_BATCH_SIZE = 100
DEFAULT_MAX_WORKERS = 4


class BatchProcessor:
    """Handles batch processing of Helm releases."""

    def __init__(
        self,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_workers: int = DEFAULT_MAX_WORKERS,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        """Initialize the batch processor.

        Args:
            batch_size: Number of items to process in each batch
            max_workers: Maximum number of parallel workers
            progress_callback: Optional callback for progress updates
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.progress_callback = progress_callback

    def process_batches(
        self,
        items: List[Any],
        process_func: Callable[[Any], Any],
        filter_func: Optional[Callable[[Any], bool]] = None,
    ) -> List[Any]:
        """Process items in batches.

        Args:
            items: List of items to process
            process_func: Function to process each item
            filter_func: Optional function to filter items before processing

        Returns:
            List of processed items
        """
        total_items = len(items)
        processed_items = []
        current_batch = []

        logger.info(
            "Starting batch processing",
            extra={
                "total_items": total_items,
                "batch_size": self.batch_size,
                "max_workers": self.max_workers,
            },
        )

        for i, item in enumerate(items, 1):
            if filter_func and not filter_func(item):
                continue

            current_batch.append(item)

            if len(current_batch) >= self.batch_size or i == total_items:
                batch_results = self._process_batch(current_batch, process_func)
                processed_items.extend(batch_results)
                current_batch = []

                if self.progress_callback:
                    self.progress_callback(i, total_items)

        logger.info(
            "Completed batch processing",
            extra={
                "total_processed": len(processed_items),
                "total_items": total_items,
            },
        )

        return processed_items

    def _process_batch(
        self,
        batch: List[Any],
        process_func: Callable[[Any], Any],
    ) -> List[Any]:
        """Process a single batch of items.

        Args:
            batch: List of items to process
            process_func: Function to process each item

        Returns:
            List of processed items
        """
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_item = {executor.submit(process_func, item): item for item in batch}
            for future in concurrent.futures.as_completed(future_to_item):
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    item = future_to_item[future]
                    logger.error(
                        "Error processing item",
                        extra={
                            "error": str(e),
                            "item": str(item),
                        },
                    )
        return results


def filter_release_by_age(
    release: Dict[str, Any],
    prefix: str,
    cutoff_time: datetime,
) -> bool:
    """Filter a release based on its age and prefix.

    Args:
        release: Helm release data
        prefix: Prefix to match against
        cutoff_time: Time threshold for filtering

    Returns:
        bool: True if the release matches the criteria
    """
    release_name = release.get("name")
    updated_str = release.get("updated")

    if not release_name or not updated_str:
        return False

    if not release_name.startswith(prefix):
        return False

    try:
        updated_time = datetime.fromisoformat(updated_str)
        if updated_time.tzinfo is None:
            updated_time = updated_time.replace(tzinfo=timezone.utc)
        else:
            updated_time = updated_time.astimezone(timezone.utc)

        return updated_time < cutoff_time
    except (ValueError, TypeError):
        return False


def process_release(release: Dict[str, Any]) -> Optional[str]:
    """Process a single release.

    Args:
        release: Helm release data

    Returns:
        Optional[str]: Release name if valid, None otherwise
    """
    try:
        release_name = release.get("name")
        if not release_name:
            return None
        return release_name
    except Exception as e:
        logger.error(
            "Error processing release",
            extra={
                "error": str(e),
                "release": str(release),
            },
        )
        return None 