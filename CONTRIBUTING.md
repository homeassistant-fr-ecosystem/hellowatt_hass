# Contributing to HelloWatt Home Assistant Integration

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Development Setup

### Prerequisites

- Python 3.11 or 3.12
- Git
- A HelloWatt account (for testing)

### Initial Setup

1. **Clone the repository**

```bash
git clone https://github.com/homeassistant-fr-ecosystem/hellowatt_hass.git
cd hellowatt_hass
```

2. **Create a virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**

```bash
pip install -r requirements-dev.txt
```

4. **Install pre-commit hooks** (recommended)

```bash
pre-commit install
```

This will automatically run linting and formatting checks before each commit.

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_client.py

# Run in verbose mode
pytest -v
```

### Code Quality Checks

#### Linting with Ruff

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .
```

#### Formatting with Black

```bash
# Check formatting
black --check .

# Auto-format
black .
```

#### Import Sorting with isort

```bash
# Check import order
isort --check-only .

# Auto-sort imports
isort .
```

#### Type Checking with Mypy

```bash
# Run type checker
mypy custom_components/hellowatt
```

#### Run All Checks

```bash
# Using pre-commit (recommended)
pre-commit run --all-files

# Or manually:
ruff check . && black --check . && isort --check-only . && mypy custom_components/hellowatt
```

## Code Style Guidelines

### Python Style

- Follow [PEP 8](https://pep8.org/)
- Use Black for formatting (line length: 88)
- Use type hints for all functions and methods
- Write docstrings for all public functions, classes, and methods

### Type Hints

All code should include comprehensive type hints:

```python
from typing import Any

def process_data(data: dict[str, Any], count: int) -> list[str]:
    """Process data and return results.

    Args:
        data: Input data dictionary
        count: Number of items to process

    Returns:
        List of processed items
    """
    return [str(item) for item in data.values()][:count]
```

### Docstrings

Use Google-style docstrings:

```python
def authenticate(username: str, password: str) -> bool:
    """Authenticate user with HelloWatt API.

    Args:
        username: User email address
        password: User password

    Returns:
        True if authentication successful, False otherwise

    Raises:
        ValueError: If username or password is empty
        ConnectionError: If unable to connect to API
    """
    if not username or not password:
        raise ValueError("Username and password required")
    # ... implementation
```

## Testing Guidelines

### Writing Tests

- Write tests for all new features
- Maintain or improve code coverage (target: 70%+)
- Use descriptive test names: `test_<what>_<condition>_<expected>`
- Group related tests in classes

Example:

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
class TestHelloWattClient:
    """Tests for HelloWatt API client."""

    async def test_get_consumption_returns_data_when_api_responds(
        self, mock_client
    ):
        """Test that get_consumption returns data when API responds successfully."""
        # Arrange
        mock_client._request_with_retry = AsyncMock(
            return_value={"values": [{"kwh": 10}]}
        )

        # Act
        result = await mock_client.get_daily_consumption("home123", start, end)

        # Assert
        assert result["values"][0]["kwh"] == 10
```

### Test Coverage

- Run coverage reports: `pytest --cov --cov-report=html`
- View report: open `htmlcov/index.html`
- Critical paths should have >90% coverage

## Pull Request Process

### Before Submitting

1. **Update your branch**

```bash
git checkout main
git pull origin main
git checkout your-feature-branch
git rebase main
```

2. **Run all checks**

```bash
pytest --cov
pre-commit run --all-files
```

3. **Update documentation** if needed
   - Update README.md for user-facing changes
   - Update DEVELOPER.md for technical changes
   - Add/update docstrings

### Submitting a PR

1. **Create a clear title**
   - Use conventional commits format: `feat:`, `fix:`, `docs:`, `refactor:`, etc.
   - Example: `feat: add support for multi-home accounts`

2. **Write a good description**
   - What changes were made?
   - Why were they made?
   - How to test?
   - Any breaking changes?

3. **Ensure CI passes**
   - All tests must pass
   - Linting must pass
   - Type checking must pass
   - Code coverage should not decrease

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Example:

```
feat(client): add retry logic with exponential backoff

- Implement exponential backoff for API retries
- Add configurable max retry attempts
- Improve error handling for transient failures

Closes #42
```

## Project Structure

```
hellowatt_hass/
├── .github/
│   └── workflows/          # CI/CD workflows
├── custom_components/
│   └── hellowatt/          # Integration code
│       ├── __init__.py         # Setup & service registration
│       ├── client.py           # API client
│       ├── config_flow.py      # Configuration UI and options flow
│       ├── const.py            # Constants
│       ├── coordinator.py      # Data coordinator
│       ├── diagnostics.py      # HA diagnostics support
│       ├── importer.py         # Historical data import & statistics
│       ├── manifest.json       # Integration metadata
│       ├── sensor.py           # Sensor platform
│       ├── services.yaml       # Service definitions
│       ├── strings.json        # UI strings
│       └── system_health.py    # System health reporting
├── tests/                  # Test files
├── pyproject.toml          # Tool configurations
├── requirements-dev.txt    # Dev dependencies
└── README.md               # User documentation
```

## Getting Help

- **Issues**: Check [existing issues](https://github.com/homeassistant-fr-ecosystem/hellowatt_hass/issues)
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: See README.md and DEVELOPER.md

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help create a welcoming environment

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing! 🎉
