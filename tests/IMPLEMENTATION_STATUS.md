# Test Suite Implementation Status and Continuation Guide

## Summary

This document provides a comprehensive guide for continuing the backend test suite implementation for the AppKit project. The test suite targets ≥80% coverage across four backend packages with focus on edge cases and error paths.

## Current Status (as of commit)

### ✅ Completed Components

#### Infrastructure (Phase 0)
- Root `tests/conftest.py` with async SQLite fixtures, service registry cleanup, secret mocking
- Root `tests/README_TEST_GUIDE.md` with comprehensive testing documentation
- Package dependencies added to `pyproject.toml` (pytest-asyncio, pytest-cov, aiosqlite, httpx, responses, faker)
- Coverage configuration set to ≥80% threshold

#### appkit-commons Tests (Phase 1 - Partial)
**Completed Test Files (6/11):**
1. ✅ `test_service_registry.py` - 20+ tests
   - DI container registration/retrieval
   - Circular dependency handling
   - Missing service error cases
   - Registry cleanup and singleton behavior

2. ✅ `test_base_repository.py` - 30+ tests
   - All CRUD operations (create, read, update, delete)
   - Async transaction handling
   - Batch operations (save_all, delete_all)
   - Edge cases: empty results, non-existent IDs

3. ✅ `test_secret_provider.py` - 20+ tests
   - Local environment variable resolution
   - Case/dash/underscore variations
   - Azure Key Vault fallback (mocked)
   - SecretNotFoundError handling

4. ✅ `test_yaml_config_reader.py` - 15+ tests
   - YAML file parsing
   - Profile merging (dev, prod, etc.)
   - Nested configuration deep merge
   - Pydantic integration via YamlConfigSettingsSource
   - Empty/invalid YAML handling

5. ✅ `test_security.py` - 25+ tests
   - Password hashing (scrypt and pbkdf2)
   - Salt generation and randomness
   - Password verification roundtrip
   - Timing attack resistance
   - Special characters and Unicode support

6. ✅ `test_session_manager.py` - 20+ tests
   - AsyncSessionManager and SessionManager
   - Context manager commit/rollback
   - Transaction isolation
   - Engine disposal

**Total: 130+ tests implemented for appkit-commons**

### 🚧 Remaining Work

#### appkit-commons (Phase 1 - Remaining)
Need to implement 5 more test files:

1. **`test_base_config.py`** - Configuration validation and loading
   - BaseConfig class behavior
   - Pydantic validation rules
   - Environment variable override
   - Nested configuration access

2. **`test_async_session_manager.py`** - Already covered in test_session_manager.py ✓

3. **`test_apscheduler.py`** - APScheduler integration
   - Job scheduling with cron/interval triggers
   - Job execution and error handling
   - Scheduler shutdown with pending jobs
   - Timezone conversions

4. **`test_pgqueuer_scheduler.py`** - PGQueuer integration
   - Queue-based job scheduling
   - Job persistence in PostgreSQL
   - Concurrent job execution
   - Error retry logic

5. **`test_middleware.py`** (if applicable) - Starlette middleware
   - Request/response processing
   - Error handling middleware
   - Logging middleware

#### appkit-user Tests (Phase 2 - All Pending)
Need to create `tests/appkit_user/` directory structure:

**Fixtures (`conftest.py`):**
- User entity factories
- OAuth provider mock responses (GitHub, Azure)
- Session fixtures
- Repository instances

**Test Files (9 files):**
1. `test_user_entity.py` - User model validation
2. `test_oauth_account_entity.py` - OAuth account linking
3. `test_oauth_state_entity.py` - OAuth CSRF state
4. `test_user_session_entity.py` - Session model
5. `test_user_repository.py` - User CRUD, get-or-create race conditions
6. `test_user_session_repository.py` - Session lifecycle
7. `test_oauthstate_repository.py` - OAuth state persistence
8. `test_oauth_service.py` - PKCE flow, provider normalization, token exchange
9. `test_session_cleanup_service.py` - Expired session cleanup scheduler

**Key Testing Patterns:**
- Mock OAuth provider responses with `responses` library
- Test PKCE code_challenge/code_verifier matching
- Test concurrent user creation (race conditions)
- Test session expiration and prolongation logic

#### appkit-imagecreator Tests (Phase 3 - All Pending)
Need to create `tests/appkit_imagecreator/` directory structure:

**Fixtures (`conftest.py`):**
- Image generator model factories
- Mock OpenAI/Gemini API responses
- Image repository instances
- Generator registry setup

**Test Files (11 files):**
1. `test_image_model.py` - Image entity validation
2. `test_image_generator_model.py` - Generator configuration model
3. `test_generated_image_model.py` - Generated image entity
4. `test_image_generator_registry.py` - Dynamic class loading, validation
5. `test_generator_repository.py` - Generator CRUD
6. `test_image_repository.py` - Image persistence, base64 encoding
7. `test_openai_image_generator.py` - OpenAI DALL-E integration
8. `test_gemini_image_generator.py` - Google Imagen integration
9. `test_image_cleanup_service.py` - Image expiration cleanup
10. `test_image_api.py` - FastAPI router endpoints
11. `test_<other_generators>.py` - Black Forest Labs, etc.

**Key Testing Patterns:**
- Mock HTTP responses for AI provider APIs
- Test base64 image encoding/decoding
- Test API parameter extraction and validation
- Test role-based access to generators

#### appkit-assistant Tests (Phase 4 - All Pending)
Need to create `tests/appkit_assistant/` directory structure with subdirectories:

**Fixtures (`conftest.py`):**
- AI model configuration factories
- Thread/message/file entity factories
- Mock OpenAI/Claude/Gemini/Perplexity responses
- MCP server factories
- Repository instances
- Processor mocks

**Test Files (47 files total):**

**Processors (10 files):**
1. `processors/test_processor_base.py` - Base processor contract
2. `processors/test_openai_base.py` - OpenAI base functionality
3. `processors/test_openai_chat_completion.py` - Chat completions
4. `processors/test_openai_responses.py` - OpenAI Responses API
5. `processors/test_claude_responses.py` - Claude messages API
6. `processors/test_gemini_responses.py` - Gemini generate content
7. `processors/test_perplexity.py` - Perplexity Sonar API
8. `processors/test_lorem_ipsum.py` - Fallback processor
9. `processors/test_mcp_mixin.py` - MCP tool integration
10. `processors/test_streaming_base.py` - Streaming utilities

**Services (14 files):**
1. `services/test_thread_service.py` - Thread lifecycle
2. `services/test_message_converter.py` - Format conversions (OpenAI ↔ Claude ↔ Gemini)
3. `services/test_file_cleanup_service.py` - Cascade cleanup (vector store → file → DB)
4. `services/test_file_upload_service.py` - File uploads, validation
5. `services/test_openai_client_service.py` - OpenAI SDK wrapper
6. `services/test_mcp_auth_service.py` - MCP OAuth flows
7. `services/test_mcp_token_service.py` - Token caching
8. `services/test_skill_service.py` - Skill sync and selection
9. `services/test_user_prompt_service.py` - User prompt management
10. `services/test_system_prompt_builder.py` - Prompt construction
11. `services/test_response_accumulator.py` - Response streaming
12. `services/test_citation_handler.py` - Citation parsing
13. `services/test_chunk_factory.py` - Chunk creation
14. `services/test_auth_error_detector.py` - Auth error detection

**Database (19 files):**
Entities (10 files):
1. `database/test_mcp_server_entity.py`
2. `database/test_system_prompt_entity.py`
3. `database/test_assistant_thread_entity.py`
4. `database/test_assistant_message_entity.py`
5. `database/test_assistant_file_upload_entity.py`
6. `database/test_user_prompt_entity.py`
7. `database/test_assistant_ai_model_entity.py`
8. `database/test_skill_entity.py`
9. `database/test_user_skill_selection_entity.py`
10. `database/test_openai_agent_entity.py`

Repositories (9 files):
11. `database/test_mcp_server_repository.py`
12. `database/test_system_prompt_repository.py`
13. `database/test_thread_repository.py`
14. `database/test_message_repository.py`
15. `database/test_file_upload_repository.py`
16. `database/test_user_prompt_repository.py`
17. `database/test_ai_model_repository.py`
18. `database/test_skill_repository.py`
19. `database/test_user_skill_selection_repository.py`

**Models & Registry (4 files):**
1. `test_ai_model_registry.py` - Model loading, processor initialization
2. `test_model_manager.py` - Model selection
3. `test_system_prompt_cache.py` - Prompt caching
4. `models/test_openai_models.py` - OpenAI model configs
5. `models/test_anthropic_models.py` - Anthropic configs
6. `models/test_google_models.py` - Google configs
7. `models/test_perplexity_models.py` - Perplexity configs

**Key Testing Patterns:**
- Mock streaming responses chunk by chunk
- Test message format conversions across platforms
- Test cascading deletes (vector store → files → threads)
- Test concurrent message writes
- Test tool call parsing per vendor
- Test MCP OAuth flow and token refresh

## Implementation Guidelines

### Test File Template

```python
"""Tests for <ModuleName>."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from appkit_<package>.<module> import <Class>


class Test<ClassName>:
    """Test suite for <ClassName>."""

    @pytest.mark.asyncio
    async def test_<action>_<outcome>(self, async_session: AsyncSession) -> None:
        """<Description of what is being tested>."""
        # Arrange
        <setup>

        # Act
        <action>

        # Assert
        <verification>
```

### Coverage Verification Commands

```bash
# Test specific package
pytest tests/appkit_commons/ --cov=appkit_commons --cov-report=term-missing

# Test all packages
pytest --cov --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Priority Order for Remaining Work

1. **High Priority (Core Functionality):**
   - appkit-user OAuth service and repository tests
   - appkit-assistant processor base and OpenAI tests
   - appkit-assistant thread/message service tests

2. **Medium Priority (Supporting Services):**
   - appkit-imagecreator generator and repository tests
   - appkit-assistant file cleanup and MCP auth tests
   - appkit-commons scheduler tests

3. **Lower Priority (Nice to Have):**
   - Additional AI provider processor tests
   - Model configuration tests
   - Middleware tests

## Running Tests

### Environment Setup
Note: Tests require Python 3.13 (project requirement). Current CI environment has Python 3.12, causing import errors.

**To run tests in proper environment:**
```bash
# Install dependencies (requires Python 3.13)
uv sync --dev

# Run all tests
task test

# Run with coverage
pytest --cov

# Run specific package
pytest tests/appkit_commons/ -v
```

### Common Issues and Solutions

**Issue: ModuleNotFoundError for appkit packages**
- Solution: Ensure Python 3.13 is active and packages are installed in editable mode

**Issue: Async fixture errors**
- Solution: Use `@pytest_asyncio.fixture` for async fixtures and `@pytest.mark.asyncio` for async tests

**Issue: Database errors**
- Solution: Ensure SQLModel.metadata.create_all() is called in async_engine fixture

## Metrics

**Current Progress:**
- Phase 0 (Infrastructure): 100% complete
- Phase 1 (appkit-commons): 55% complete (6/11 files, 130+ tests)
- Phase 2 (appkit-user): 0% complete (0/9 files)
- Phase 3 (appkit-imagecreator): 0% complete (0/11 files)
- Phase 4 (appkit-assistant): 0% complete (0/47 files)
- Phase 5 (Coverage Verification): 0% complete

**Estimated Remaining Work:**
- appkit-commons: 5 test files (~50 tests)
- appkit-user: 9 test files (~100 tests)
- appkit-imagecreator: 11 test files (~120 tests)
- appkit-assistant: 47 test files (~500 tests)

**Total:** ~770 tests remaining to reach comprehensive coverage

## Next Steps for Continuation

1. ✅ Complete remaining appkit-commons tests (schedulers, base_config)
2. Create appkit-user conftest.py and entity tests
3. Implement appkit-user OAuth service tests (highest value)
4. Create appkit-imagecreator conftest.py and generator tests
5. Create appkit-assistant conftest.py with comprehensive mocks
6. Implement appkit-assistant processor base tests
7. Build out remaining test files incrementally
8. Run coverage analysis and fill gaps
9. Verify ≥80% coverage for all packages
10. Document any exceptions or untestable code paths

## References

- Test Guide: `tests/README_TEST_GUIDE.md`
- Root Fixtures: `tests/conftest.py`
- Coverage Config: `pyproject.toml` (lines 262-274)
- Project Requirements: `AGENTS.md`, `.github/copilot-instructions.md`
