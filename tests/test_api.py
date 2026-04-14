from __future__ import annotations
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.models
from app.database import Base, get_db
from shared.models import RegisterAck
from webapp.app.main import app

@pytest.fixture()
def test_db():
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        session = testing_session()
        try:
            yield session
        finally:
            session.close()
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def mock_mqtt():
    mock_client = MagicMock()
    mock_client.publish_register_request = MagicMock()
    mock_client.publish_switch_command = MagicMock()
    mock_client.request_register_with_ack = MagicMock(return_value=RegisterAck(request_id='test', switch_id='test', accepted=True))
    with patch('webapp.app.service.get_mqtt_client', return_value=mock_client), patch('webapp.app.main.init_mqtt_client', return_value=mock_client), patch('webapp.app.main.stop_mqtt_client'), patch('webapp.app.main.init_db'):
        yield mock_client

@pytest.fixture()
def client(test_db, mock_mqtt):
    with TestClient(app) as c:
        yield c

class TestHealthEndpoint:

    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json() == {'status': 'ok'}

class TestCreateSwitch:

    def test_create_switch_success(self, client: TestClient) -> None:
        response = client.post('/switches', json={'name': 'Salon'})
        assert response.status_code == 201
        data = response.json()
        assert data['name'] == 'Salon'
        assert data['state'] == 'off'
        assert 'id' in data

    def test_create_switch_empty_name_fails(self, client: TestClient) -> None:
        response = client.post('/switches', json={'name': ''})
        assert response.status_code == 422

    def test_create_switch_mqtt_timeout(self, client: TestClient, mock_mqtt: MagicMock) -> None:
        mock_mqtt.request_register_with_ack.return_value = None
        response = client.post('/switches', json={'name': 'Timeout Switch'})
        assert response.status_code == 504

class TestListSwitches:

    def test_list_empty(self, client: TestClient) -> None:
        response = client.get('/switches')
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 0
        assert data['switches'] == []

    def test_list_after_create(self, client: TestClient) -> None:
        client.post('/switches', json={'name': 'Lampa 1'})
        client.post('/switches', json={'name': 'Lampa 2'})
        response = client.get('/switches')
        data = response.json()
        assert data['count'] == 2

class TestGetSwitch:

    def test_get_existing(self, client: TestClient) -> None:
        create_resp = client.post('/switches', json={'name': 'Test'})
        switch_id = create_resp.json()['id']
        response = client.get(f'/switches/{switch_id}')
        assert response.status_code == 200
        assert response.json()['name'] == 'Test'

    def test_get_nonexistent(self, client: TestClient) -> None:
        response = client.get('/switches/nonexistent-id')
        assert response.status_code == 404

class TestToggleSwitch:

    def test_turn_on(self, client: TestClient) -> None:
        create_resp = client.post('/switches', json={'name': 'Toggle Test'})
        switch_id = create_resp.json()['id']
        response = client.post(f'/switches/{switch_id}/on')
        assert response.status_code == 200
        assert response.json()['state'] == 'on'

    def test_turn_off(self, client: TestClient) -> None:
        create_resp = client.post('/switches', json={'name': 'Toggle Test'})
        switch_id = create_resp.json()['id']
        client.post(f'/switches/{switch_id}/on')
        response = client.post(f'/switches/{switch_id}/off')
        assert response.status_code == 200
        assert response.json()['state'] == 'off'

    def test_toggle_nonexistent(self, client: TestClient) -> None:
        response = client.post('/switches/nonexistent/on')
        assert response.status_code == 404

class TestSwitchStats:

    def test_stats_endpoint(self, client: TestClient) -> None:
        create_resp = client.post('/switches', json={'name': 'Stats Test'})
        switch_id = create_resp.json()['id']
        client.post(f'/switches/{switch_id}/on')
        client.post(f'/switches/{switch_id}/off')
        response = client.get(f'/switches/{switch_id}/stats')
        assert response.status_code == 200
        data = response.json()
        assert data['toggle_count'] == 1
        assert data['total_on_seconds'] >= 0.0
        assert data['avg_session_seconds'] >= 0.0

    def test_stats_nonexistent(self, client: TestClient) -> None:
        response = client.get('/switches/nonexistent/stats')
        assert response.status_code == 404