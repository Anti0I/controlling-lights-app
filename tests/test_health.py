from unittest.mock import patch
from fastapi.testclient import TestClient
from webapp.app.main import app

def test_health_endpoint_returns_ok() -> None:
    with patch('webapp.app.main.init_mqtt_client'), patch('webapp.app.main.stop_mqtt_client'):
        with TestClient(app) as client:
            response = client.get('/health')
        assert response.status_code == 200
        assert response.json() == {'status': 'ok'}