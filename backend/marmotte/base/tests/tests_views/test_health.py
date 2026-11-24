from django.test import Client


class TestHealthView:
    def test_returns_ok_and_version(self, client: Client) -> None:
        """GET /api/health tells that the service is up, with its version."""
        # WHEN
        response = client.get("/api/health")
        # THEN
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "0.1.0"}


class TestApiDocs:
    def test_page_renders(self, client: Client) -> None:
        """The interactive API documentation is served."""
        # WHEN
        response = client.get("/api/docs")
        # THEN
        assert response.status_code == 200
