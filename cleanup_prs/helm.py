"""Helm operations for the cleanup-prs tool."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .batch_processor import BatchProcessor, filter_release_by_age, process_release
from .exceptions import (
    CleanupError,
    ErrorContext,
    HelmUninstallError,
    with_retry,
)
from .kubernetes import run_command
from .logging_config import get_logger
from .performance import get_performance_monitor, monitor_performance

logger = get_logger(__name__)


@with_retry(max_retries=3, delay=1.0)
@monitor_performance("list_helm_releases")
def list_helm_releases(namespace: str) -> List[Dict[str, Any]]:
    """Lists Helm releases in the specified namespace in JSON format.

    Args:
        namespace: Kubernetes namespace to list releases from

    Returns:
        List of Helm releases

    Raises:
        CleanupError: If there's an error listing releases
    """
    monitor = get_performance_monitor()
    monitor.start_operation("list_helm_releases", namespace=namespace)

    logger.info("Listing Helm releases", extra={"namespace": namespace})
    try:
        result = run_command(
            [
                "helm",
                "list",
                "--namespace",
                namespace,
                "--output",
                "json",
                "--time-format",
                "2006-01-02T15:04:05Z07:00",
            ],
            capture=True,
        )
        # Handle empty output (no releases found)
        if not result.stdout or result.stdout.strip().lower() == "null":
            logger.info("No Helm releases found", extra={"namespace": namespace})
            monitor.end_operation(success=True, count=0)
            return []
        releases = json.loads(result.stdout)
        logger.info(
            "Found Helm releases",
            extra={"namespace": namespace, "count": len(releases)},
        )
        monitor.end_operation(success=True, count=len(releases))
        return releases
    except json.JSONDecodeError as e:
        monitor.end_operation(
            success=False,
            error="Failed to parse Helm list output",
            details={"namespace": namespace, "output": result.stdout},
        )
        raise CleanupError(
            "Failed to parse Helm list output",
            ErrorContext(
                timestamp=datetime.now(),
                operation="list_helm_releases",
                details={
                    "namespace": namespace,
                    "output": result.stdout,
                },
            ),
        ) from e
    except Exception as e:
        monitor.end_operation(
            success=False,
            error="An unexpected error occurred during helm list",
            details={"namespace": namespace},
        )
        raise CleanupError(
            "An unexpected error occurred during helm list",
            ErrorContext(
                timestamp=datetime.now(),
                operation="list_helm_releases",
                details={"namespace": namespace},
            ),
        ) from e


@monitor_performance("filter_old_pr_releases")
def filter_old_pr_releases(
    releases: List[Dict[str, Any]],
    prefix: str,
    days_threshold: int,
    batch_size: Optional[int] = None,
    max_workers: Optional[int] = None,
) -> List[str]:
    """Filters releases based on name prefix and age using batch processing.

    Args:
        releases: List of Helm releases
        prefix: Prefix to match release names against
        days_threshold: Age threshold in days
        batch_size: Optional batch size for processing
        max_workers: Optional maximum number of parallel workers

    Returns:
        List of release names to delete
    """
    monitor = get_performance_monitor()
    monitor.start_operation(
        "filter_old_pr_releases",
        prefix=prefix,
        days_threshold=days_threshold,
        total_releases=len(releases),
        batch_size=batch_size,
        max_workers=max_workers,
    )

    now = datetime.now(timezone.utc)
    cutoff_time = now - timedelta(days=days_threshold)

    logger.info(
        "Filtering old PR releases",
        extra={
            "prefix": prefix,
            "days_threshold": days_threshold,
            "cutoff_time": cutoff_time.isoformat(),
            "total_releases": len(releases),
        },
    )

    # Create a filter function with the current parameters
    def filter_func(release: Dict[str, Any]) -> bool:
        return filter_release_by_age(release, prefix, cutoff_time)

    # Initialize batch processor
    processor = BatchProcessor(
        batch_size=batch_size,
        max_workers=max_workers,
    )

    # Process releases in batches
    old_releases = processor.process_batches(
        items=releases,
        process_func=process_release,
        filter_func=filter_func,
    )

    logger.info(
        "Found releases matching criteria",
        extra={
            "count": len(old_releases),
            "releases": old_releases,
        },
    )

    monitor.end_operation(
        success=True,
        count=len(old_releases),
        total_releases=len(releases),
    )
    return old_releases


@with_retry(max_retries=3, delay=1.0)
@monitor_performance("delete_helm_release")
def delete_helm_release(release_name: str, namespace: str, dry_run: bool = False) -> None:
    """Deletes a specific Helm release.

    Args:
        release_name: Name of the Helm release to delete
        namespace: Kubernetes namespace
        dry_run: If True, only simulate the deletion without actually deleting

    Raises:
        HelmUninstallError: If the uninstall operation fails
    """
    monitor = get_performance_monitor()
    monitor.start_operation(
        "delete_helm_release",
        release=release_name,
        namespace=namespace,
        dry_run=dry_run,
    )

    logger.info(
        "Deleting Helm release",
        extra={
            "release": release_name,
            "namespace": namespace,
            "dry_run": dry_run,
        },
    )
    try:
        cmd = ["helm", "uninstall", release_name, "--namespace", namespace]
        if dry_run:
            cmd.append("--dry-run")
        run_command(cmd)
        logger.info(
            "Helm uninstall command ran",
            extra={"release": release_name, "dry_run": dry_run},
        )
        monitor.end_operation(success=True)
    except CleanupError as e:
        monitor.end_operation(
            success=False,
            error=f"Failed to uninstall Helm release '{release_name}'",
            details={
                "release_name": release_name,
                "namespace": namespace,
                "dry_run": dry_run,
            },
        )
        raise HelmUninstallError(
            f"Failed to uninstall Helm release '{release_name}'",
            ErrorContext(
                timestamp=datetime.now(),
                operation="delete_helm_release",
                details={
                    "release_name": release_name,
                    "namespace": namespace,
                    "dry_run": dry_run,
                },
            ),
        ) from e
