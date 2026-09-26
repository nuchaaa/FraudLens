import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


def test_http_liveness_and_docs() -> None:
    with TestClient(create_app(Settings(environment="test", _env_file=None))) as client:
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "version": "0.1.0",
            "stage": "transaction-api",
        }
        assert client.get("/docs").status_code == 200
        assert client.post("/transactions", json={}).status_code == 404


def test_production_hides_documentation() -> None:
    app = create_app(Settings(environment="production", database_url=None, _env_file=None))
    assert app.docs_url is None and app.openapi_url is None
    with pytest.raises(ValueError, match="PostgreSQL runtime login"), TestClient(app):
        pass


def test_database_secret_not_exposed() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://user:secret@localhost/db", _env_file=None
    )
    assert "secret" not in repr(settings)
