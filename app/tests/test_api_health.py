from fastapi.testclient import TestClient
from app.api.routes import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_health_check_head():
    response = client.head("/health")
    # HEAD request should return 200 OK
    assert response.status_code == 200
    # response.text should be empty for HEAD usually, but let's just check status.
    # verify headers if needed, but status code is the main thing proving method is allowed.
