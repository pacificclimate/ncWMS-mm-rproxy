import pytest
from unittest.mock import patch, MagicMock
from ncwms_mm_rproxy import create_app


@pytest.fixture
def app():
    config = {
        "TESTING": True,
        "NCWMS_URL": "http://example.com/fake-ncwms",
        "TRANSLATION_CACHE": {},
        "NCWMS_LAYER_PARAM_NAMES": "LAYER",
        "NCWMS_DATASET_PARAM_NAMES": "",
        "EXCLUDED_REQUEST_HEADERS": "",
        "EXCLUDED_RESPONSE_HEADERS": "",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    }

    # Patch preload to avoid DB call during app startup
    with patch("ncwms_mm_rproxy.Translation.preload"):
        return create_app(config)


@pytest.fixture
def client(app):
    return app.test_client()


class TestAppEndpoints:
    def test_healthz(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.data == b"OK"

    @patch("ncwms_mm_rproxy.requests.get")
    def test_dynamic_success_response(self, mock_get, client):
        # Simulate a successful response from the proxied request
        mock_get.return_value = MagicMock(
            status_code=200, raw=b"mocked", headers={}, url="http://example.com/final"
        )

        # Trigger the dynamic proxy route
        response = client.get("/dynamic/dyn1?LAYER=abc")

        # Validate response was forwarded correctly
        assert response.status_code == 200
        assert response.data == b"mocked"
        mock_get.assert_called_once()

    @patch("ncwms_mm_rproxy.requests.get")
    def test_dynamic_retries_on_failure(self, mock_get, client):
        # First call fails, second succeeds
        mock_get.side_effect = [
            MagicMock(status_code=404, raw=b"fail", headers={}),
            MagicMock(status_code=200, raw=b"ok", headers={}),
        ]

        response = client.get("/dynamic/prefix?LAYER=abc")

        assert response.status_code == 200
        assert response.data == b"ok"
        assert mock_get.call_count == 2
