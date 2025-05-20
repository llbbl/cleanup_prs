"""Kubernetes operations for the cleanup-prs tool."""

import subprocess
from datetime import datetime
from typing import List, Dict, Any
import logging
from .exceptions import (
    CleanupError, KubernetesError, ContextNotFoundError,
    with_retry, ErrorContext
)
from .logging_config import get_logger

logger = get_logger(__name__)

def run_command(command: List[str], check: bool = True, capture: bool = False, text: bool = True, shell: bool = False) -> subprocess.CompletedProcess:
    """Runs a shell command using subprocess.
    
    Args:
        command: Command to run as a list of strings
        check: Whether to check the return code
        capture: Whether to capture stdout/stderr
        text: Whether to return text output
        shell: Whether to run in shell mode
    
    Returns:
        CompletedProcess instance
    
    Raises:
        CleanupError: If command execution fails
    """
    logger.debug("Running command", extra={"command": " ".join(command)})
    try:
        result = subprocess.run(
            command,
            check=check,
            capture_output=capture,
            text=text,
            shell=shell
        )
        if capture:
            logger.debug("Command output", extra={
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip() if result.stderr else None
            })
        return result
    except FileNotFoundError as e:
        raise CleanupError(
            f"Command '{command[0]}' not found. Is it installed and in your PATH?",
            ErrorContext(
                timestamp=datetime.now(),
                operation="run_command",
                details={"command": command}
            )
        ) from e
    except subprocess.CalledProcessError as e:
        raise CleanupError(
            f"Error running command: {' '.join(command)}",
            ErrorContext(
                timestamp=datetime.now(),
                operation="run_command",
                details={
                    "command": command,
                    "return_code": e.returncode,
                    "stdout": e.stdout,
                    "stderr": e.stderr
                }
            )
        ) from e
    except Exception as e:
        raise CleanupError(
            f"An unexpected error occurred while running command: {' '.join(command)}",
            ErrorContext(
                timestamp=datetime.now(),
                operation="run_command",
                details={"command": command}
            )
        ) from e

@with_retry(max_retries=3, delay=1.0)
def set_kubectl_context(context_name: str) -> None:
    """Sets the kubectl context to the specified name.
    
    Args:
        context_name: Name of the kubectl context to use
    
    Raises:
        ContextNotFoundError: If the context doesn't exist
        CleanupError: If there's an error setting the context
    """
    logger.info("Setting kubectl context", extra={"context": context_name})
    try:
        # Check context existence silently first
        subprocess.run(
            ["kubectl", "config", "get-contexts", context_name],
            check=True,
            capture_output=True,
            text=True
        )
        logger.debug("Context found", extra={"context": context_name})
    except subprocess.CalledProcessError as e:
        raise ContextNotFoundError(
            f"Kubectl context '{context_name}' not found.",
            ErrorContext(
                timestamp=datetime.now(),
                operation="set_kubectl_context",
                details={"context_name": context_name}
            )
        ) from e

    run_command(["kubectl", "config", "use-context", context_name])
    logger.info("Kubectl context set", extra={"context": context_name}) 