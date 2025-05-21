"""Secret management for the cleanup-prs tool.

This module provides functionality for managing sensitive data and credentials
in a secure manner. It handles:
- Kubernetes credentials
- Helm credentials
- File permissions
- Configuration security
"""

import os
import stat
from pathlib import Path
from typing import Optional

from .exceptions import CleanupError, ErrorContext
from .logging_config import get_logger

logger = get_logger(__name__)


class SecretManager:
    """Manages secrets and sensitive data for the cleanup-prs tool."""

    def __init__(self):
        """Initialize the secret manager."""
        self._kubeconfig_path: Optional[Path] = None
        self._helm_config_path: Optional[Path] = None

    def set_kubeconfig_path(self, path: str) -> None:
        """Set and validate the kubeconfig path.

        Args:
            path: Path to the kubeconfig file

        Raises:
            CleanupError: If the kubeconfig file is not secure
        """
        kubeconfig = Path(path)
        if not kubeconfig.exists():
            raise CleanupError(
                f"Kubeconfig file not found: {path}",
                ErrorContext(
                    operation="set_kubeconfig_path",
                    details={"path": path},
                ),
            )

        # Check file permissions
        mode = kubeconfig.stat().st_mode
        if mode & (stat.S_IROTH | stat.S_IWOTH):
            raise CleanupError(
                f"Kubeconfig file has insecure permissions: {path}",
                ErrorContext(
                    operation="set_kubeconfig_path",
                    details={"path": path, "mode": oct(mode)},
                ),
            )

        self._kubeconfig_path = kubeconfig
        logger.debug("Kubeconfig path set", extra={"path": str(kubeconfig)})

    def set_helm_config_path(self, path: str) -> None:
        """Set and validate the Helm config path.

        Args:
            path: Path to the Helm config directory

        Raises:
            CleanupError: If the Helm config directory is not secure
        """
        helm_config = Path(path)
        if not helm_config.exists():
            raise CleanupError(
                f"Helm config directory not found: {path}",
                ErrorContext(
                    operation="set_helm_config_path",
                    details={"path": path},
                ),
            )

        # Check directory permissions
        mode = helm_config.stat().st_mode
        if mode & (stat.S_IROTH | stat.S_IWOTH):
            raise CleanupError(
                f"Helm config directory has insecure permissions: {path}",
                ErrorContext(
                    operation="set_helm_config_path",
                    details={"path": path, "mode": oct(mode)},
                ),
            )

        self._helm_config_path = helm_config
        logger.debug("Helm config path set", extra={"path": str(helm_config)})

    def secure_file(self, path: str, mode: int = 0o600) -> None:
        """Set secure permissions on a file.

        Args:
            path: Path to the file
            mode: File permissions (default: 0o600)

        Raises:
            CleanupError: If the file cannot be secured
        """
        try:
            os.chmod(path, mode)
            logger.debug("File permissions set", extra={"path": path, "mode": oct(mode)})
        except OSError as e:
            raise CleanupError(
                f"Failed to set secure permissions on file: {path}",
                ErrorContext(
                    operation="secure_file",
                    details={"path": path, "mode": oct(mode)},
                ),
            ) from e

    def secure_directory(self, path: str, mode: int = 0o700) -> None:
        """Set secure permissions on a directory.

        Args:
            path: Path to the directory
            mode: Directory permissions (default: 0o700)

        Raises:
            CleanupError: If the directory cannot be secured
        """
        try:
            os.chmod(path, mode)
            logger.debug("Directory permissions set", extra={"path": path, "mode": oct(mode)})
        except OSError as e:
            raise CleanupError(
                f"Failed to set secure permissions on directory: {path}",
                ErrorContext(
                    operation="secure_directory",
                    details={"path": path, "mode": oct(mode)},
                ),
            ) from e

    def validate_config_file(self, path: str) -> None:
        """Validate the security of a configuration file.

        Args:
            path: Path to the configuration file

        Raises:
            CleanupError: If the configuration file is not secure
        """
        config_path = Path(path)
        if not config_path.exists():
            raise CleanupError(
                f"Configuration file not found: {path}",
                ErrorContext(
                    operation="validate_config_file",
                    details={"path": path},
                ),
            )

        # Check file permissions
        mode = config_path.stat().st_mode
        if mode & (stat.S_IROTH | stat.S_IWOTH):
            raise CleanupError(
                f"Configuration file has insecure permissions: {path}",
                ErrorContext(
                    operation="validate_config_file",
                    details={"path": path, "mode": oct(mode)},
                ),
            )

        logger.debug("Configuration file validated", extra={"path": str(config_path)}) 