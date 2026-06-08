from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.schemas import BatchDocument, BatchStatus

client = TestClient(app)


def test_health_live():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@patch("app.routes.batches.db.list_batches", new_callable=AsyncMock, return_value=[])
def test_batches_open_when_auth_disabled(_mock_list):
    response = client.get("/api/v1/batches")
    assert response.status_code == 200


def test_batches_require_auth(monkeypatch):
    monkeypatch.setenv("ENFORCE_AUTH", "true")
    monkeypatch.setenv("API_KEYS", "test-secret-key-32chars-minimum")
    get_settings.cache_clear()

    response = client.get("/api/v1/batches")
    assert response.status_code == 401


@patch("app.routes.batches.db.list_batches", new_callable=AsyncMock, return_value=[])
def test_batches_with_auth_header(_mock_list, monkeypatch):
    monkeypatch.setenv("ENFORCE_AUTH", "true")
    monkeypatch.setenv("API_KEYS", "test-secret-key-32chars-minimum")
    get_settings.cache_clear()

    response = client.get("/api/v1/batches", headers={"X-API-Key": "test-secret-key-32chars-minimum"})
    assert response.status_code == 200


def test_invalid_batch_id_returns_404():
    response = client.get("/api/v1/batch/not-a-valid-id")
    assert response.status_code == 404


@patch(
    "app.routes.batches.db.get_batch",
    new_callable=AsyncMock,
    return_value=BatchDocument(
        id="507f1f77bcf86cd799439011",
        status=BatchStatus.UNDER_REVIEW,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        page_inputs=[],
        page_count=1,
    ),
)
def test_upload_rejects_under_review(_mock_get_batch):
    response = client.post("/api/v1/batch/507f1f77bcf86cd799439011/upload")
    assert response.status_code == 400
