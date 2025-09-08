# Test Organization Guide

## 📋 Overview
Tests are organized by **USER STORIES** to provide clear visibility for Product Owners and developers.

## 🗂️ Folder Structure

```
tests/
├── auth/                           # Authentication related stories
│   ├── AUTH-001_user_login/        # User Login Story
│   │   ├── unit/                   # Unit tests (mocked dependencies)
│   │   │   └── test_login_unit.py
│   │   └── integration/            # Integration tests (real DB/API)
│   │       └── test_login_integration.py
│   ├── AUTH-002_user_logout/       # User Logout Story (Sprint 2)
│   │   ├── unit/
│   │   └── integration/
│   ├── AUTH-003_session_management/ # Session Management (Sprint 2)
│   │   ├── unit/
│   │   └── integration/
│   └── AUTH-004_password_security/  # Password Security (Sprint 1 - Complete)
│       ├── unit/
│       │   ├── test_security_unit.py
│       │   └── test_user_model_unit.py
│       └── integration/
├── ai/                             # AI/ML related stories  
│   └── AI-001_langchain_setup/     # LangChain Setup (Sprint 1 - Complete)
│       ├── unit/
│       └── integration/
│           └── test_agents_integration.py
└── conftest.py                     # Shared test fixtures

```

## 🏃 Running Tests

### Run all tests for a specific user story:
```bash
# Run all AUTH-001 tests (unit + integration)
pytest tests/auth/AUTH-001_user_login/ -v

# Run only unit tests for AUTH-001
pytest tests/auth/AUTH-001_user_login/unit/ -v

# Run only integration tests for AUTH-001
pytest tests/auth/AUTH-001_user_login/integration/ -v
```

### Run all tests for a feature area:
```bash
# Run all authentication tests
pytest tests/auth/ -v

# Run all AI tests
pytest tests/ai/ -v
```

### Run tests by type:
```bash
# Run all unit tests
pytest tests/**/unit/ -v

# Run all integration tests (requires database)
./database/scripts/setup-dev-db.sh  # Start DB first
pytest tests/**/integration/ -v
```

## 📊 Test Coverage by Story

| Story ID | Story Name | Unit Tests | Integration Tests | Status |
|----------|------------|------------|-------------------|--------|
| AUTH-001 | User Login | ✅ 16 tests | ✅ 13 tests | Complete |
| AUTH-002 | User Logout | 🔄 Pending | 🔄 Pending | Sprint 2 |
| AUTH-003 | Session Management | 🔄 Pending | 🔄 Pending | Sprint 2 |
| AUTH-004 | Password Security | ✅ Complete | ✅ Complete | Sprint 1 |
| AI-001 | LangChain Setup | ✅ Complete | ✅ Complete | Sprint 1 |

## 🧪 Test Types

### Unit Tests (`unit/` folders)
- Fast execution (no external dependencies)
- Mocked database, APIs, and services
- Focus on business logic
- Run frequently during development

### Integration Tests (`integration/` folders)
- Test real interactions with database and APIs
- Require PostgreSQL and Redis running
- Test full request/response cycles
- Run before committing and in CI/CD

## 📝 Adding New Tests

When implementing a new user story:

1. Create the folder structure:
   ```bash
   mkdir -p tests/<feature>/<STORY-ID>_<story_name>/{unit,integration}
   touch tests/<feature>/<STORY-ID>_<story_name>/__init__.py
   ```

2. Add unit tests in `unit/test_<feature>_unit.py`
3. Add integration tests in `integration/test_<feature>_integration.py`
4. Update this README with the new story status

## 🔍 Finding Tests

As a Product Owner, you can easily find tests for any story:
- Navigate to `tests/<feature>/<STORY-ID>_<description>/`
- Unit tests show the business logic implementation
- Integration tests show the actual user experience

## 🚀 Best Practices

1. **Keep tests with their stories** - Don't create generic test files
2. **Name tests clearly** - `test_<what_it_does>_<expected_result>`
3. **Update test status** - Mark stories as complete when all tests pass
4. **Run tests before PR** - Both unit and integration tests must pass