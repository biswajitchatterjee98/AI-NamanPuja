import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("USE_MOCK_LLM", "true")
os.environ.setdefault("ENFORCE_AUTH", "false")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DATABASE", "namanpuja_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")


@pytest.fixture
def anyio_backend():
    return "asyncio"
