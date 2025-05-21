# Cleanup PRs - Usage Guide

This guide provides examples of how to use the cleanup-prs tool effectively.

## Basic Usage

The most basic usage requires specifying the Kubernetes context, namespace, release prefix, and age threshold:

```bash
cleanup-prs \
  --context "my-cluster" \
  --namespace "my-namespace" \
  --prefix "pr-" \
  --days 7
```

This will:

1. Connect to the specified Kubernetes cluster
2. Look for Helm releases in the given namespace
3. Find releases that:
   - Start with "pr-"
   - Are older than 7 days
4. Prompt for confirmation before deletion

## Dry Run Mode

To preview what would be deleted without actually deleting anything:

```bash
cleanup-prs \
  --context "my-cluster" \
  --namespace "my-namespace" \
  --prefix "pr-" \
  --days 7 \
  --dry-run
```

## Force Mode

To skip the confirmation prompt and delete matching releases immediately:

```bash
cleanup-prs \
  --context "my-cluster" \
  --namespace "my-namespace" \
  --prefix "pr-" \
  --days 7 \
  --force
```

## Logging Configuration

### Basic Logging

Enable verbose logging and specify a log file:

```bash
cleanup-prs \
  --context "my-cluster" \
  --namespace "my-namespace" \
  --prefix "pr-" \
  --days 7 \
  --verbose \
  --log-file "/var/log/cleanup-prs.log"
```

### Custom Log Format

#### JSON Format

Specify which fields to include in JSON logs:

```bash
cleanup-prs \
  --context "my-cluster" \
  --namespace "my-namespace" \
  --prefix "pr-" \
  --days 7 \
  --log-file "/var/log/cleanup-prs.log" \
  --log-format "timestamp level message function"
```

#### Text Format

Use standard Python logging format strings:

```bash
cleanup-prs \
  --context "my-cluster" \
  --namespace "my-namespace" \
  --prefix "pr-" \
  --days 7 \
  --no-json-logging \
  --log-file "/var/log/cleanup-prs.log" \
  --log-format "%(asctime)s | %(levelname)s | %(message)s"
```

### Log Rotation

#### Size-based Rotation

Rotate logs when they reach 10MB, keeping 5 backup files:

```bash
cleanup-prs \
  --context "my-cluster" \
  --namespace "my-namespace" \
  --prefix "pr-" \
  --days 7 \
  --log-file "/var/log/cleanup-prs.log" \
  --max-log-size 10 \
  --log-backup-count 5
```

#### Time-based Rotation

Rotate logs daily at midnight:

```bash
cleanup-prs \
  --context "my-cluster" \
  --namespace "my-namespace" \
  --prefix "pr-" \
  --days 7 \
  --log-file "/var/log/cleanup-prs.log" \
  --rotate-when "midnight" \
  --rotate-interval 1
```

#### Weekly Rotation

Rotate logs every Monday:

```bash
cleanup-prs \
  --context "my-cluster" \
  --namespace "my-namespace" \
  --prefix "pr-" \
  --days 7 \
  --log-file "/var/log/cleanup-prs.log" \
  --rotate-when "W0" \
  --rotate-interval 1
```

## Complete Example

Here's a complete example combining multiple features:

```bash
cleanup-prs \
  --context "my-cluster" \
  --namespace "my-namespace" \
  --prefix "pr-" \
  --days 7 \
  --verbose \
  --log-file "/var/log/cleanup-prs.log" \
  --log-format "timestamp level message function" \
  --max-log-size 10 \
  --log-backup-count 5 \
  --rotate-when "midnight" \
  --rotate-interval 1
```

This will:

1. Connect to "my-cluster"
2. Look for releases in "my-namespace"
3. Find releases starting with "pr-" older than 7 days
4. Use verbose logging
5. Write logs to "/var/log/cleanup-prs.log"
6. Include timestamp, level, message, and function in JSON logs
7. Rotate logs when they reach 10MB
8. Keep 5 backup files
9. Also rotate logs daily at midnight
10. Prompt for confirmation before deletion

## Exit Codes

The tool uses the following exit codes:

- `0`: Success
- `1`: Error occurred during execution

## Error Handling

The tool provides detailed error messages and logs for various scenarios:

- Invalid Kubernetes context
- Missing or invalid namespace
- Permission issues
- Network problems
- Invalid configuration

Check the log file for detailed error information when issues occur.
