# HelloWatt Integration Tests

This directory contains tests for the HelloWatt Home Assistant integration.

## Running Tests

### Install Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov --cov-report=html
```

Then open `htmlcov/index.html` in your browser to view the coverage report.

### Run Specific Test File

```bash
pytest tests/test_client.py
```

### Run Specific Test

```bash
pytest tests/test_client.py::TestHelloWattApiClient::test_init
```

### Run Tests in Verbose Mode

```bash
pytest -v
```

## Test Structure

- `conftest.py` - Shared fixtures and test configuration
- `test_client.py` - Tests for the API client
- `test_coordinator.py` - Tests for the data coordinator (TODO)
- `test_sensor.py` - Tests for sensor entities (TODO)
- `test_config_flow.py` - Tests for configuration flow (TODO)

## Writing Tests

### Async Tests

Use `pytest.mark.asyncio` for async tests:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Using Fixtures

Fixtures are defined in `conftest.py`:

```python
def test_with_fixture(mock_hellowatt_client):
    assert mock_hellowatt_client.username == "test@example.com"
```

### Mocking

Use `unittest.mock` for mocking:

```python
from unittest.mock import AsyncMock, Mock, patch

@pytest.mark.asyncio
async def test_with_mock():
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"key": "value"})
    # ... test code
```

## Coverage Goals

- Target: 70%+ overall coverage
- All new code should include tests
- Critical paths (authentication, data fetching) should have >90% coverage
