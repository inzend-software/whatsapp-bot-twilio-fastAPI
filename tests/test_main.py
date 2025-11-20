from fastapi.testclient import TestClient
from app.main import app, init_db
import os

client = TestClient(app)

def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json().get('status') == 'ok'

def test_webhook_secret_blocked():
    # no secret provided -> 403
    r = client.post('/webhook', json={})
    assert r.status_code == 403 or r.status_code == 422
