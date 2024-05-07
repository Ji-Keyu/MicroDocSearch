import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_upload_endpoint():
    response = client.post("/upload")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_ocr_endpoint():
    response = client.post("/ocr")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_extract_endpoint():
    response = client.post("/extract")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
