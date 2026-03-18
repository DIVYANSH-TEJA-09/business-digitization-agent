"""
Pytest configuration and shared fixtures
"""
import os
import sys
import pytest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_data_dir():
    """Get test data directory path"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def temp_storage_dir(tmp_path_factory):
    """Create temporary storage directory for tests"""
    return tmp_path_factory.mktemp("storage")
