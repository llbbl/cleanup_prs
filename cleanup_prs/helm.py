"""Helm operations for the cleanup-prs tool."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from .exceptions import (
    CleanupError,
    ErrorContext,
    HelmUninstallError,
    with_retry,
)
from .kubernetes import run_command
from .logging_config import get_logger

logger = get_logger(__name__)


@with_retry(max_retries=3, delay=1.0)
def list_helm_releases(namespace: str) -> List[Dict[str, Any]]:
    """Lists Helm releases in the specified namespace in JSON format.

    Args:
        namespace: Kubernetes namespace to list releases from

    Returns:
        List of Helm releases

    Raises:
        CleanupError: If there's an error listing releases
    """
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
            return []
        releases = json.loads(result.stdout)
        logger.info(
            "Found Helm releases",
            extra={"namespace": namespace, "count": len(releases)},
        )
        return releases
    except json.JSONDecodeError as e:
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
        raise CleanupError(
            "An unexpected error occurred during helm list",
            ErrorContext(
                timestamp=datetime.now(),
                operation="list_helm_releases",
                details={"namespace": namespace},
            ),
        ) from e


def filter_old_pr_releases(releases: List[Dict[str, Any]], prefix: str, days_threshold: int) -> List[str]:
    """Filters releases based on name prefix and age.

    Args:
        releases: List of Helm releases
        prefix: Prefix to match release names against
        days_threshold: Age threshold in days

    Returns:
        List of release names to delete
    """
    old_releases = []
    now = datetime.now(timezone.utc)
    cutoff_time = now - timedelta(days=days_threshold)

    logger.info(
        "Filtering old PR releases",
        extra={
            "prefix": prefix,
            "days_threshold": days_threshold,
            "cutoff_time": cutoff_time.isoformat(),
        },
    )

    for release in releases:
        release_name = release.get("name")
        updated_str = release.get("updated")

        if not release_name or not updated_str:
            logger.warning("Skipping release with missing data", extra={"release": release})
            continue

        if release_name.startswith(prefix):
            try:
                updated_time = datetime.fromisoformat(updated_str)
                if updated_time.tzinfo is None:
                    logger.warning(
                        "Release updated time lacks timezone",
                        extra={
                            "release": release_name,
                            "updated_time": updated_str,
                        },
                    )
                    updated_time = updated_time.replace(tzinfo=timezone.utc)
                else:
                    updated_time = updated_time.astimezone(timezone.utc)

                if updated_time < cutoff_time:
                    logger.debug(
                        "Found old PR release",
                        extra={
                            "release": release_name,
                            "updated_time": updated_time.isoformat(),
                        },
                    )
                    old_releases.append(release_name)
            except ValueError:
                logger.warning(
                    "Could not parse update timestamp",
                    extra={
                        "release": release_name,
                        "updated_time": updated_str,
                    },
                )
            except Exception as e:
                logger.warning(
                    "Error processing release",
                    extra={
                        "release": release_name,
                        "error": str(e),
                    },
                )

    logger.info(
        "Found releases matching criteria",
        extra={
            "count": len(old_releases),
            "releases": old_releases,
        },
    )
    return old_releases


@with_retry(max_retries=3, delay=1.0)
def delete_helm_release(release_name: str, namespace: str) -> None:
    """Deletes a specific Helm release.

    Args:
        release_name: Name of the Helm release to delete
        namespace: Kubernetes namespace

    Raises:
        HelmUninstallError: If the uninstall operation fails
    """
    logger.info(
        "Deleting Helm release",
        extra={
            "release": release_name,
            "namespace": namespace,
        },
    )
    try:
        run_command(["helm", "uninstall", release_name, "--namespace", namespace])
        logger.info(
            "Helm uninstall command ran",
            extra={"release": release_name},
        )
    except CleanupError as e:
        raise HelmUninstallError(
            f"Failed to uninstall Helm release '{release_name}'",
            ErrorContext(
                timestamp=datetime.now(),
                operation="delete_helm_release",
                details={
                    "release_name": release_name,
                    "namespace": namespace,
                },
            ),
        ) from e
