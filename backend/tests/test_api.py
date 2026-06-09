from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.schemas import BatchDocument, BatchStatus, PageInput

client = TestClient(app)


def test_health_live():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_llm_mock():
    response = client.get("/api/v1/health/llm")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"mock", "ok"}


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


@patch("app.routes.batches.cancel_generation_for_batch")
@patch(
    "app.routes.batches.db.transition_batch_status",
    new_callable=AsyncMock,
    return_value=True,
)
@patch(
    "app.routes.batches.db.get_batch",
    new_callable=AsyncMock,
    return_value=BatchDocument(
        id="507f1f77bcf86cd799439011",
        status=BatchStatus.GENERATING,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        page_inputs=[PageInput(puja="Ganesh Puja", city="Austin", state="Texas", country="USA")],
        page_count=1,
        generation_metadata={"generation_job_id": "job-123"},
    ),
)
def test_cancel_batch(_mock_get_batch, _mock_transition, _mock_cancel):
    response = client.post("/api/v1/batch/507f1f77bcf86cd799439011/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    _mock_cancel.assert_called_once_with("507f1f77bcf86cd799439011", "job-123")


@patch("app.routes.batches.db.delete_batch", new_callable=AsyncMock, return_value=True)
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
def test_delete_batch(_mock_get_batch, _mock_delete):
    response = client.delete("/api/v1/batch/507f1f77bcf86cd799439011")
    assert response.status_code == 200
    assert response.json()["deleted"] is True


@patch(
    "app.routes.batches.db.get_batch",
    new_callable=AsyncMock,
    return_value=BatchDocument(
        id="507f1f77bcf86cd799439011",
        status=BatchStatus.GENERATING,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        page_inputs=[],
        page_count=1,
    ),
)
def test_delete_batch_requires_stop(_mock_get_batch):
    response = client.delete("/api/v1/batch/507f1f77bcf86cd799439011")
    assert response.status_code == 400
