"""Shared test fixtures for candidate feature tests."""

import pytest
import sys
from pathlib import Path

# Add the backend directory to Python path for database imports
backend_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

pytest_plugins = ["app.features.auth.tests.conftest"]