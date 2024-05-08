import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.post("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

# TODO: file upload test across types, success and failure, no file, multiple files, different sizes, corrupted files?
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
