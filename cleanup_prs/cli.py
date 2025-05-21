"""Command-line interface for the cleanup-prs tool.

This module provides the main CLI interface for the cleanup-prs tool, which helps
clean up old Helm releases in Kubernetes clusters. It handles argument parsing,
user interaction, and orchestrates the cleanup process.

The tool supports:
- Filtering releases by age and prefix
- Dry run mode for previewing changes
- Interactive confirmation
- Configurable logging
- Multiple output formats
- Secure credential management
- Input validation
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from .exceptions import CleanupError, ValidationError
from .helm import delete_helm_release, filter_old_pr_releases, list_helm_releases
from .kubernetes import set_kubectl_context
from .logging_config import get_logger, setup_logging
from .secret_manager import SecretManager
from .validators import (
    validate_age_threshold,
    validate_file_path,
    validate_kubernetes_name,
    validate_log_format,
    validate_release_prefix,
    validate_rotation_settings,
)

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    This function sets up the argument parser with all supported command line options.
    Each argument is documented with its purpose and requirements.

    Returns:
        argparse.Namespace: Parsed command line arguments containing:
            - context: Kubernetes context to use
            - namespace: Target Kubernetes namespace
            - prefix: Release name prefix to match
            - days: Age threshold in days
            - dry_run: Whether to perform a dry run
            - force: Skip confirmation prompt
            - verbose: Enable verbose logging
            - no_json_logging: Disable JSON logging format
            - log_file: Path to log file
            - log_format: Custom format string for logs
            - max_log_size: Maximum log file size in MB
            - log_backup_count: Number of backup files to keep
            - rotate_when: When to rotate logs (S,M,H,D,W0-W6,midnight)
            - rotate_interval: Interval for time-based rotation
            - no_compress_logs: Disable log compression
            - kubeconfig: Path to kubeconfig file
            - helm_config: Path to Helm config directory
    """
    parser = argparse.ArgumentParser(description="Clean up old Helm releases in Kubernetes clusters")
    parser.add_argument(
        "--context",
        required=True,
        help="Kubernetes context to use",
    )
    parser.add_argument(
        "--namespace",
        required=True,
        help="Kubernetes namespace to clean up",
    )
    parser.add_argument(
        "--prefix",
        required=True,
        help="Prefix to match release names against",
    )
    parser.add_argument(
        "--days",
        type=int,
        required=True,
        help="Age threshold in days",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--no-json-logging",
        action="store_true",
        help="Disable JSON logging format",
    )
    parser.add_argument(
        "--log-file",
        help="Path to log file",
    )
    parser.add_argument(
        "--log-format",
        help="Custom format string for logs. For JSON format, specify space-separated field names. "
        "For text format, use standard Python logging format strings.",
    )
    parser.add_argument(
        "--max-log-size",
        type=int,
        help="Maximum log file size in MB before rotation",
    )
    parser.add_argument(
        "--log-backup-count",
        type=int,
        default=4,
        help="Number of backup files to keep (default: 4)",
    )
    parser.add_argument(
        "--rotate-when",
        choices=["S", "M", "H", "D", "W0", "W1", "W2", "W3", "W4", "W5", "W6", "midnight"],
        help="When to rotate logs (S=seconds, M=minutes, H=hours, D=days, W0-W6=weekday, midnight)",
    )
    parser.add_argument(
        "--rotate-interval",
        type=int,
        help="Interval for time-based rotation",
    )
    parser.add_argument(
        "--no-compress-logs",
        action="store_true",
        help="Disable log compression",
    )
    parser.add_argument(
        "--kubeconfig",
        help="Path to kubeconfig file (default: ~/.kube/config)",
    )
    parser.add_argument(
        "--helm-config",
        help="Path to Helm config directory (default: ~/.helm)",
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """Validate command line arguments.

    Args:
        args: Parsed command line arguments

    Raises:
        ValidationError: If any argument is invalid
    """
    # Validate Kubernetes names
    validate_kubernetes_name(args.context, "Context")
    validate_kubernetes_name(args.namespace, "Namespace")

    # Validate release prefix
    validate_release_prefix(args.prefix)

    # Validate age threshold
    validate_age_threshold(args.days)

    # Validate file paths
    if args.log_file:
        validate_file_path(args.log_file)
    if args.kubeconfig:
        validate_file_path(args.kubeconfig, must_exist=True, must_be_file=True)
    if args.helm_config:
        validate_file_path(args.helm_config, must_exist=True)

    # Validate log format
    if args.log_format:
        validate_log_format(args.log_format, not args.no_json_logging)

    # Validate rotation settings
    validate_rotation_settings(
        max_bytes=args.max_log_size * 1024 * 1024 if args.max_log_size else None,
        backup_count=args.log_backup_count,
        rotate_when=args.rotate_when,
        rotate_interval=args.rotate_interval,
    )


def confirm_deletion(releases: List[str], force: bool = False) -> bool:
    """Prompt user for confirmation before deleting releases.

    Args:
        releases: List of release names to delete
        force: If True, skip confirmation

    Returns:
        bool: True if deletion is confirmed, False otherwise
    """
    if force:
        return True

    print("\nThe following releases will be deleted:")
    for release in releases:
        print(f"  - {release}")

    while True:
        response = input("\nDo you want to continue? [y/N]: ").lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no", ""):
            return False
        print("Please answer 'y' or 'n'")


def main() -> int:
    """Main entry point for the CLI.

    This function orchestrates the entire cleanup process:
    1. Parses command line arguments
    2. Validates all inputs
    3. Sets up logging configuration
    4. Configures Kubernetes context
    5. Lists and filters Helm releases
    6. Handles dry run mode
    7. Manages user confirmation
    8. Executes deletion if confirmed

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    args = parse_args()

    try:
        # Validate all arguments
        validate_args(args)

        # Initialize secret manager
        secret_manager = SecretManager()

        # Set up credential paths
        kubeconfig_path = args.kubeconfig or os.path.expanduser("~/.kube/config")
        helm_config_path = args.helm_config or os.path.expanduser("~/.helm")

        # Validate credentials
        secret_manager.set_kubeconfig_path(kubeconfig_path)
        secret_manager.set_helm_config_path(helm_config_path)

        # Setup logging
        if args.log_file:
            # Ensure log directory exists and is secure
            log_dir = os.path.dirname(args.log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
                secret_manager.secure_directory(log_dir)

        setup_logging(
            log_file=args.log_file,
            log_level="DEBUG" if args.verbose else "INFO",
            json_format=not args.no_json_logging,
            log_format=args.log_format,
            max_bytes=args.max_log_size * 1024 * 1024 if args.max_log_size else None,
            backup_count=args.log_backup_count,
            rotate_when=args.rotate_when,
            rotate_interval=args.rotate_interval,
            compress_logs=not args.no_compress_logs,
        )

        # Set kubectl context
        set_kubectl_context(args.context)

        # List and filter releases
        releases = list_helm_releases(args.namespace)
        old_releases = filter_old_pr_releases(releases, args.prefix, args.days)

        if not old_releases:
            logger.info("No old releases found matching criteria")
            return 0

        # Handle dry run
        if args.dry_run:
            logger.info("Dry run mode - would delete releases", extra={"releases": old_releases})
            for release in old_releases:
                delete_helm_release(release, args.namespace, dry_run=True)
            return 0

        # Confirm and delete
        if confirm_deletion(old_releases, force=args.force):
            for release in old_releases:
                delete_helm_release(release, args.namespace, dry_run=False)
            logger.info("Successfully deleted all specified releases")
            return 0
        else:
            logger.info("Deletion cancelled by user")
            return 0

    except ValidationError as e:
        logger.error(
            "Validation error", extra={"error": str(e), "context": e.context.__dict__ if e.context else None}
        )
        return 1
    except CleanupError as e:
        logger.error(
            "Error during cleanup", extra={"error": str(e), "context": e.context.__dict__ if e.context else None}
        )
        return 1
    except Exception as e:
        logger.error("Unexpected error", extra={"error": str(e)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
