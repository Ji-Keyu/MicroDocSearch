"""
Tests for main.py
"""

import sys
from pathlib import Path
import requests
from fastapi.testclient import TestClient
from io import BytesIO
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.main import app



client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

client = TestClient(app)

CONAN3 = "./static/conan3.pdf"
CONAN7 = "./static/conan7.tiff"
CONAN13 = "./static/conan13.jpg"
CONAN18 = "./static/conan18.png"
CONAN26 = "./static/conan26.jpg"
testfiles = [
    CONAN3,
    CONAN7,
    CONAN13,
    CONAN18,
    CONAN26,
]

def test_upload_valid_files():
    files = [("files", open(i, "rb")) for i in testfiles]
    response = client.post("/upload", files=files)
    assert response.status_code == 200, f"Expected status code 200, \
        but got {response.status_code}. Response content: {response.text}"
    assert "uploaded_files" in response.json()
    assert len(response.json()["uploaded_files"]) == len(files)
    uploaded_files = response.json()["uploaded_files"]
    for i, file in enumerate(uploaded_files):
        assert "file_id" in file, f"Expected 'file_id' in uploaded file, \
            but got: {file}. Response content: {response.text}"
        assert "signed_url" in file, f"Expected 'signed_url' in uploaded file, \
            but got: {file}. Response content: {response.text}"

        signed_url = file["signed_url"]
        downloaded_file = requests.get(signed_url, timeout=5)

        original_file_path = testfiles[i]
        with open(original_file_path, "rb") as original_file:
            original_content = original_file.read()
            assert downloaded_file.content == original_content, f"Downloaded file content does not match the original file content for file: {original_file_path}"

    for file_tuple in files:
        file_tuple[1].close()

def test_upload_invalid_file_extension():
    files = [
        ("files", ("file1.txt", BytesIO(b"Text content"), "text/plain")),
    ]
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "File type .txt is not allowed" in response.json()["detail"]

def test_upload_invalid_file_type():
    files = [
        ("files", ("file1.pdf", BytesIO(b"Text content"), "application/pdf")),
    ]
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "File type text/plain is not allowed" in response.json()["detail"]

def test_upload_file_exceeds_size_limit():
    large_file_content = b"A" * (11 * 1024 * 1024)  # 11 MB
    files = [
        ("files", ("large_file.pdf", BytesIO(large_file_content), "application/pdf")),
    ]
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "File size exceeds the maximum limit" in response.json()["detail"]

def test_upload_no_files():
    response = client.post("/upload", files=[])
    assert response.status_code == 200
    assert response.json()["uploaded_files"] == []

def test_upload_endpoint_internal_server_error(mocker):
    mocker.patch("src.main.minio_client.put_object", side_effect=Exception("Minio error"))
    files = [
        ("files", open(CONAN3, "rb"))
    ]
    response = client.post("/upload", files=files)
    assert response.status_code == 500
    assert "Error uploading file" in response.json()["detail"]

def test_ocr_endpoint():
    response = client.post("/ocr")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_extract_endpoint():
    response = client.post("/extract")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
