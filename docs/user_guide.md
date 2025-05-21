# Cleanup PRs - User Guide

## Overview

Cleanup PRs is a command-line tool designed to help manage and clean up Helm releases in Kubernetes clusters, particularly those associated with pull requests. It provides a safe and efficient way to remove old or unused releases while maintaining proper logging and error handling.

## Key Features

- **Selective Cleanup**: Target specific releases based on prefix and age
- **Safety First**: Interactive confirmation and dry-run mode
- **Flexible Logging**: Customizable log formats and rotation policies
- **Error Handling**: Comprehensive error reporting and logging

## Prerequisites

Before using the tool, ensure you have:

1. **Kubernetes Access**:

   - A valid kubeconfig file
   - Appropriate permissions to list and delete Helm releases
   - Access to the target namespace

2. **Helm Installation**:

   - Helm 3.x installed
   - Proper Helm configuration

3. **System Requirements**:
   - Python 3.11 or higher
   - Sufficient disk space for logs
   - Write permissions for log directories

## Best Practices

### Release Naming

- Use consistent prefixes for PR-related releases (e.g., `pr-`, `feature-`, `bugfix-`)
- Include PR numbers in release names for better tracking
- Avoid spaces or special characters in release names

### Logging Strategy

1. **Log Location**:

   - Use a dedicated directory for logs
   - Ensure proper permissions
   - Consider using a volume mount in containerized environments

2. **Rotation Policy**:

   - Size-based rotation for high-volume environments
   - Time-based rotation for predictable cleanup
   - Adjust backup count based on storage constraints

3. **Format Selection**:
   - Use JSON format for machine processing
   - Use text format for human readability
   - Include relevant fields for debugging

### Security Considerations

1. **Access Control**:

   - Use service accounts with minimal required permissions
   - Regularly audit access rights
   - Rotate credentials as needed

2. **Sensitive Data**:
   - Avoid logging sensitive information
   - Use appropriate log levels
   - Consider log redaction for sensitive fields

### Performance Optimization

1. **Large Clusters**:

   - Use appropriate timeouts
   - Consider batch processing for large numbers of releases
   - Monitor resource usage

2. **Log Management**:
   - Implement appropriate rotation policies
   - Monitor disk usage
   - Clean up old log files

## Common Use Cases

### Regular Cleanup

For regular maintenance of PR-related releases:

```bash
cleanup-prs \
  --context "production" \
  --namespace "pr-releases" \
  --prefix "pr-" \
  --days 7 \
  --log-file "/var/log/cleanup-prs.log" \
  --rotate-when "midnight"
```

### Emergency Cleanup

For urgent cleanup with force mode:

```bash
cleanup-prs \
  --context "production" \
  --namespace "pr-releases" \
  --prefix "pr-" \
  --days 7 \
  --force \
  --log-file "/var/log/cleanup-prs.log"
```

### Debugging Issues

For troubleshooting with verbose logging:

```bash
cleanup-prs \
  --context "production" \
  --namespace "pr-releases" \
  --prefix "pr-" \
  --days 7 \
  --verbose \
  --log-file "/var/log/cleanup-prs.log" \
  --log-format "timestamp level message function line"
```

## Troubleshooting

### Common Issues

1. **Permission Denied**:

   - Check kubeconfig permissions
   - Verify namespace access
   - Ensure proper RBAC configuration

2. **Log File Issues**:

   - Verify directory permissions
   - Check disk space
   - Ensure proper rotation configuration

3. **Connection Problems**:
   - Verify cluster connectivity
   - Check network configuration
   - Validate context settings

### Debugging Steps

1. Enable verbose logging:

   ```bash
   cleanup-prs --verbose ...
   ```

2. Check log files:

   ```bash
   tail -f /var/log/cleanup-prs.log
   ```

3. Verify Kubernetes access:
   ```bash
   kubectl get helmreleases -n <namespace>
   ```

## Integration

### CI/CD Pipelines

Example GitHub Actions workflow:

```yaml
name: Cleanup PR Releases

on:
  schedule:
    - cron: "0 0 * * *" # Daily at midnight

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: "3.8"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install cleanup-prs
      - name: Run cleanup
        run: |
          cleanup-prs \
            --context "${{ secrets.KUBE_CONTEXT }}" \
            --namespace "pr-releases" \
            --prefix "pr-" \
            --days 7 \
            --log-file "/var/log/cleanup-prs.log"
```

### Monitoring

1. **Log Monitoring**:

   - Set up log aggregation
   - Configure alerts for errors
   - Monitor rotation status

2. **Resource Monitoring**:
   - Track disk usage
   - Monitor API rate limits
   - Watch for performance issues

## Support

For issues and support:

1. Check the [GitHub repository](https://github.com/llbbl/cleanup_prs)
2. Review existing issues
3. Create a new issue with:
   - Detailed description
   - Relevant logs
   - Steps to reproduce
   - Environment information

