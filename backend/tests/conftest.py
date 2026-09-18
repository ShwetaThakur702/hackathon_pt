import os

os.environ["DATABASE_URL"] = "sqlite:///./test_nishchint.db"
os.environ["LLM_API_KEY"] = ""  # force deterministic fallback heuristics in tests

# Tests must never depend on (or be slowed/broken by) whatever real
# credentials happen to be sitting in the developer's backend/.env — force
# every external integration off here, before app.config's get_settings()
# is cached for the first time. Individual tests opt back in explicitly
# (see the cognee_enabled fixture below) with mocked HTTP calls only.
os.environ["COGNEE_ENABLED"] = "false"
os.environ["COGNEE_API_KEY"] = ""
os.environ["COGNEE_BASE_URL"] = ""
os.environ["N8N_WEBHOOK_URL"] = ""

from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.database.seed import reset_and_seed  # noqa: E402
from app.database.session import Base, SessionLocal, engine  # noqa: E402
from app.integrations.cognee.cognee_memory_service import cognee_memory_service  # noqa: E402
from app.main import app  # noqa: E402
from app import models  # noqa: E402,F401


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    reset_and_seed(db)
    yield db
    db.close()


@pytest.fixture()
def client(db_session):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def cognee_enabled():
    """Temporarily makes the CogneeMemoryService singleton report as
    configured, WITHOUT ever making a real HTTP call: `.remember`/`.recall`
    are mocked to safe no-op defaults ({"stored": True} / []) by this
    fixture itself, so a test that doesn't care about the exact memory
    content still can't accidentally hit the network. A test that wants to
    assert on call args or return a specific payload re-patches
    `.remember`/`.recall` on the yielded object with `patch.object(...)`,
    which layers on top of (and is torn down before) this fixture's mocks.

    `.configured` is a computed property (not a plain attribute), so it
    can't be patched directly; we swap the underlying `_settings` instead.
    """
    original_settings = cognee_memory_service._settings
    cognee_memory_service._settings = Settings(
        cognee_enabled=True,
        cognee_api_key="test-key",
        cognee_base_url="https://tenant.aws.cognee.ai",
        cognee_dataset="nishchint_memory",
    )
    with patch.object(cognee_memory_service, "remember", return_value={"stored": True}), \
         patch.object(cognee_memory_service, "recall", return_value=[]):
        yield cognee_memory_service
    cognee_memory_service._settings = original_settings
