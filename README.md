# Cleanup PRs

A tool for cleaning up old Helm releases in Kubernetes clusters.

## Features

- Clean up old Helm releases based on name prefix and age
- Support for multiple Kubernetes contexts
- Structured JSON logging
- Dry run mode for safety
- Interactive confirmation before deletion
- Configurable logging levels and formats

## Installation

### Using Poetry (Recommended)

1. Install [Poetry](https://python-poetry.org/docs/#installation)
2. Clone this repository
3. Install dependencies:
   ```bash
   poetry install
   ```

## Usage

```bash
# Basic usage
cleanup-prs --context my-cluster --namespace my-namespace --prefix pr- --days 7

# Dry run mode
cleanup-prs --context my-cluster --namespace my-namespace --prefix pr- --days 7 --dry-run

# Verbose logging
cleanup-prs --context my-cluster --namespace my-namespace --prefix pr- --days 7 -v

# Custom log file
cleanup-prs --context my-cluster --namespace my-namespace --prefix pr- --days 7 --log-file /path/to/logs/cleanup.log

# Disable JSON logging
cleanup-prs --context my-cluster --namespace my-namespace --prefix pr- --days 7 --no-json-logging
```

## Development

### Setup

1. Install development dependencies:

   ```bash
   poetry install --with dev
   ```

2. Install pre-commit hooks:
   ```bash
   poetry run pre-commit install
   ```

### Running Tests

```bash
poetry run pytest
```

### Code Style

This project uses:

- [Black](https://black.readthedocs.io/) for code formatting
- [isort](https://pycqa.github.io/isort/) for import sorting
- [mypy](https://mypy.readthedocs.io/) for static type checking
- [flake8](https://flake8.pycqa.org/) for linting

Run all checks:

```bash
poetry run black .
poetry run isort .
poetry run mypy .
poetry run flake8
```

## License

MIT License - see LICENSE file for details
