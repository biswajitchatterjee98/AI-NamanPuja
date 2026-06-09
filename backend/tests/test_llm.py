from app.services.llm import LlmService, slugify


def test_slugify():
    assert slugify("Ganesh Puja", "in", "Mumbai") == "ganesh-puja-in-mumbai"


def test_mock_ping():
    service = LlmService.__new__(LlmService)
    service._client = None
    service._provider = "mock"
    service._model = "mock"
    result = service.ping()
    assert result["status"] == "mock"
