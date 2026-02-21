# AppKit Test Suite Guide

## Overview

This test suite provides comprehensive coverage (≥80%) for the AppKit backend packages:
- **appkit-commons**: Configuration, database, scheduler, registry, security
- **appkit-user**: Authentication backend (OAuth, entities, repositories, session cleanup)
- **appkit-imagecreator**: Image generation backend (registry, repositories, services)
- **appkit-assistant**: AI assistant backend (processors, services, repositories, models)

## Philosophy

### Test Isolation
- Each test runs in complete isolation using SQLite in-memory databases
- Service registry is cleared between tests
- No test depends on another test's state or execution order

### Async Testing
- All async code is tested with `pytest-asyncio`
- Async fixtures use `@pytest_asyncio.fixture` decorator
- Async tests use `@pytest.mark.asyncio` marker

### Mocking Strategy
- **Database**: SQLite in-memory (`:memory:`) for fast, isolated tests
- **External APIs**: HTTP-level mocking with `responses` library or `httpx` MockTransport
- **Secrets**: Local environment variables (no real Azure Key Vault calls)

### Coverage Focus
- Happy paths: Standard use cases work correctly
- Edge cases: Boundary conditions, empty results, null values
- Error paths: Exception handling, validation failures, timeout scenarios

## Running Tests

### All Tests
```bash
# Run all tests with coverage
task test

# Or directly with pytest
pytest --cov

# With parallel execution
pytest --cov -n auto
```

### Package-Specific Tests
```bash
# Test only appkit-commons
pytest tests/appkit_commons/ --cov=appkit_commons

# Test only appkit-user
pytest tests/appkit_user/ --cov=appkit_user

# Test only appkit-imagecreator
pytest tests/appkit_imagecreator/ --cov=appkit_imagecreator

# Test only appkit-assistant
pytest tests/appkit_assistant/ --cov=appkit_assistant
```

### Specific Test Files
```bash
# Test a single file
pytest tests/appkit_commons/test_service_registry.py -v

# Test a specific test class
pytest tests/appkit_commons/test_service_registry.py::TestServiceRegistry -v

# Test a specific test function
pytest tests/appkit_commons/test_service_registry.py::TestServiceRegistry::test_register_and_get -v
```

### Coverage Reports
```bash
# Generate HTML coverage report
pytest --cov --cov-report=html

# View in browser
open htmlcov/index.html

# Generate terminal report
pytest --cov --cov-report=term-missing
```

## Fixture Architecture

### Root Fixtures (`tests/conftest.py`)
Shared across all tests:

- **async_engine**: SQLite in-memory async engine
- **async_session_factory**: Session factory for creating new sessions
- **async_session**: Fresh async session for each test (auto-rollback)
- **clean_service_registry**: Service registry cleared before/after each test
- **mock_secret_provider**: Forces local secret provider (no Azure)
- **mock_secrets**: Common test secrets in environment variables
- **faker_instance**: Faker for generating test data
- **temp_dir**: Temporary directory for file operations
- **captured_logs**: Capture log output for assertions

### Package Fixtures
Each package has its own `conftest.py` with specialized fixtures:

#### appkit-commons (`tests/appkit_commons/conftest.py`)
- Entity factories for config models
- YAML config file factories
- Repository instances pre-configured

#### appkit-user (`tests/appkit_user/conftest.py`)
- User entity factories
- OAuth session mocks (GitHub, Azure)
- User/session/OAuth state repositories
- Mock OAuth provider responses

#### appkit-imagecreator (`tests/appkit_imagecreator/conftest.py`)
- Image generator model factories
- Mock OpenAI/Gemini image API responses
- Image generator registry pre-configured
- Image repository with test data

#### appkit-assistant (`tests/appkit_assistant/conftest.py`)
- Thread/message/file entity factories
- Mock AI model API responses (OpenAI, Claude, Gemini, Perplexity)
- MCP server factories and mock SSE servers
- All repository instances
- Processor mocks

## Common Testing Patterns

### Pattern 1: Async Test with Session
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_create_user(async_session: AsyncSession, user_factory):
    # Arrange
    user = await user_factory(email="test@example.com")

    # Act
    await async_session.commit()

    # Assert
    assert user.id is not None
    assert user.email == "test@example.com"
```

### Pattern 2: Testing Error Paths
```python
import pytest

@pytest.mark.asyncio
async def test_get_nonexistent_user_raises(user_repository, async_session):
    # Act & Assert
    with pytest.raises(ValueError, match="User not found"):
        await user_repository.get_by_id(async_session, 99999)
```

### Pattern 3: Mocking HTTP Responses
```python
import responses

@responses.activate
def test_oauth_fetch_user():
    # Arrange
    responses.add(
        responses.GET,
        "https://api.github.com/user",
        json={"id": 123, "email": "user@example.com"},
        status=200
    )

    # Act
    result = fetch_github_user("fake-token")

    # Assert
    assert result["email"] == "user@example.com"
```

### Pattern 4: Using Faker for Test Data
```python
from faker import Faker

def test_with_fake_data(faker_instance: Faker):
    # Arrange
    email = faker_instance.email()
    name = faker_instance.name()

    # Act
    user = create_user(email=email, name=name)

    # Assert
    assert user.email == email
```

### Pattern 5: Testing Async Context Managers
```python
@pytest.mark.asyncio
async def test_session_context_manager(async_session_factory):
    # Act
    async with async_session_factory() as session:
        # Use session
        result = await session.execute(select(User))
        users = result.scalars().all()

    # Assert
    assert isinstance(users, list)
```

### Pattern 6: Capturing Log Output
```python
import logging

def test_with_logs(captured_logs):
    # Arrange
    logger = logging.getLogger("my_module")

    # Act
    logger.info("Test message")

    # Assert
    assert "Test message" in captured_logs.text
    assert any(record.levelname == "INFO" for record in captured_logs.records)
```

## Writing New Tests

### Test File Naming
- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test functions: `test_<what_it_tests>_<expected_outcome>`

Examples:
```
test_user_repository.py
    TestUserRepository
        test_create_user_success
        test_create_user_duplicate_email_raises
        test_find_by_email_not_found_returns_none
```

### Test Organization
```python
"""Tests for UserRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

class TestUserRepository:
    """Test suite for UserRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, async_session: AsyncSession):
        """Creating a new user succeeds and assigns an ID."""
        # Test implementation
        pass

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email_raises(self, async_session: AsyncSession):
        """Creating a user with duplicate email raises IntegrityError."""
        # Test implementation
        pass
```

### Edge Cases to Cover
For each class/method, ensure tests cover:

1. **Happy path**: Standard use case works
2. **Empty input**: Handles empty strings, lists, None values
3. **Invalid input**: Rejects malformed data with proper exceptions
4. **Not found**: Gracefully handles missing data (None, empty list, or exception)
5. **Duplicate/conflict**: Handles uniqueness violations
6. **Async cleanup**: Resources released properly on exceptions
7. **Transaction rollback**: DB state consistent after errors

## Debugging Tests

### Verbose Output
```bash
# Show all test names and outcomes
pytest -v

# Show print statements
pytest -s

# Show local variables on failure
pytest -l

# Stop on first failure
pytest -x
```

### Debugging with Breakpoints
```python
def test_debug_example():
    import pdb; pdb.set_trace()  # Breakpoint
    # Or use pytest's breakpoint()
    breakpoint()
```

### Async Debugging
```python
@pytest.mark.asyncio
async def test_async_debug():
    import asyncio
    # Use logging instead of print for async
    logger.debug("Current state: %s", some_variable)
```

### Coverage Gaps
```bash
# Show lines not covered by tests
pytest --cov --cov-report=term-missing

# Focus on specific module
pytest --cov=appkit_commons.registry --cov-report=term-missing
```

## Continuous Integration

Tests run automatically on:
- Every push to PR branches
- PR merge to main
- Release tags

### CI Requirements
- All tests must pass
- Coverage must be ≥80% per package
- No skipped tests (unless explicitly documented)
- Linting passes (ruff)

## Tips and Best Practices

### DO
✓ Use async fixtures for async code
✓ Clear service registry between tests
✓ Mock external APIs at HTTP level
✓ Test both success and failure paths
✓ Use descriptive test names
✓ Keep tests focused and isolated
✓ Use factories for creating test data

### DON'T
✗ Share state between tests
✗ Make real API calls
✗ Depend on test execution order
✗ Skip tests without documentation
✗ Test implementation details (test behavior)
✗ Use production secrets or databases
✗ Leave flaky tests unfixed

## Troubleshooting

### Import Errors
```
ModuleNotFoundError: No module named 'appkit_commons'
```
**Solution**: Install dev dependencies
```bash
uv sync --dev
```

### Async Fixture Errors
```
ScopeMismatch: You tried to access the function scoped fixture event_loop
```
**Solution**: Use `@pytest_asyncio.fixture` for async fixtures

### Database Errors
```
sqlalchemy.exc.OperationalError: no such table
```
**Solution**: Ensure `SQLModel.metadata.create_all()` is called in `async_engine` fixture

### Secret Provider Errors
```
SecretNotFoundError: Secret 'xyz' not found
```
**Solution**: Use `mock_secret_provider` and `mock_secrets` fixtures

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [SQLAlchemy async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Faker documentation](https://faker.readthedocs.io/)
