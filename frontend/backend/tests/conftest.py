import os
from pathlib import Path

import pytest
from assistant_web_backend.dependencies import get_storage
from assistant_web_backend.main import app
from assistant_web_backend.storage import Storage
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path) -> TestClient:
    """Create a test client with isolated storage."""
    repo_root = Path(__file__).resolve().parents[3]
    os.environ.setdefault("PLAYGROUND_CONFIG_DIR", str(repo_root / "config"))

    test_storage = Storage(tmp_path / "test.db")

    # Override dependency to use test storage
    app.dependency_overrides[get_storage] = lambda: test_storage

    yield TestClient(app)

    # Clean up override after test
    app.dependency_overrides.clear()
