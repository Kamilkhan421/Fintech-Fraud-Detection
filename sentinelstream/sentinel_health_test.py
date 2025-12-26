from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
resp = client.get('/health')
print(resp.status_code)
print(resp.json())
