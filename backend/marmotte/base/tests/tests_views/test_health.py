from django.test import Client


def test_health_returns_ok_and_version(client: Client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_api_docs_page_renders(client: Client) -> None:
    response = client.get("/api/docs")
    assert response.status_code == 200
