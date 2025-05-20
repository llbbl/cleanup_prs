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
"""

import argparse
import sys
from typing import List

from .exceptions import CleanupError
from .helm import delete_helm_release, filter_old_pr_releases, list_helm_releases
from .kubernetes import set_kubectl_context
from .logging_config import get_logger, setup_logging

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
            - verbose: Enable verbose logging
            - no_json_logging: Disable JSON logging format
            - log_file: Path to log file
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
    return parser.parse_args()


def confirm_deletion(releases: List[str]) -> bool:
    """Ask for user confirmation before deletion.

    This function displays the list of releases that will be deleted and prompts
    the user for confirmation. It handles various forms of yes/no responses and
    provides clear feedback.

    Args:
        releases: List of release names that will be deleted

    Returns:
        bool: True if user confirms deletion, False if user cancels
    """
    if not releases:
        return False

    print("\nThe following releases will be deleted:")
    for release in releases:
        print(f"  - {release}")

    while True:
        response = input("\nDo you want to proceed? (y/N): ").lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no", ""):
            return False
        print("Please answer 'y' or 'n'")


def main() -> int:
    """Main entry point for the CLI.

    This function orchestrates the entire cleanup process:
    1. Parses command line arguments
    2. Sets up logging configuration
    3. Configures Kubernetes context
    4. Lists and filters Helm releases
    5. Handles dry run mode
    6. Manages user confirmation
    7. Executes deletion if confirmed

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    args = parse_args()

    # Setup logging
    setup_logging(
        log_file=args.log_file,
        log_level="DEBUG" if args.verbose else "INFO",
        json_format=not args.no_json_logging,
    )

    try:
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
            return 0

        # Confirm and delete
        if confirm_deletion(old_releases):
            for release in old_releases:
                delete_helm_release(release, args.namespace)
            logger.info("Successfully deleted all specified releases")
            return 0
        else:
            logger.info("Deletion cancelled by user")
            return 0

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
