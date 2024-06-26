"""
Tests for main.py
"""

import sys
from pathlib import Path
from io import BytesIO
from unittest.mock import Mock
import requests
from fastapi.testclient import TestClient
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

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

INDEX = "microdocsearch"

# def test_upload_valid_files():
#     files = [("files", open(i, "rb")) for i in testfiles]
#     response = client.post("/upload", files=files)
#     assert response.status_code == 200, f"Expected status code 200, \
#         but got {response.status_code}. Response content: {response.text}"
#     assert "uploaded_files" in response.json()
#     assert len(response.json()["uploaded_files"]) == len(files)
#     uploaded_files = response.json()["uploaded_files"]
#     for i, file in enumerate(uploaded_files):
#         assert "file_id" in file, f"Expected 'file_id' in uploaded file, \
#             but got: {file}. Response content: {response.text}"
#         assert "signed_url" in file, f"Expected 'signed_url' in uploaded file, \
#             but got: {file}. Response content: {response.text}"

#         signed_url = file["signed_url"]
#         downloaded_file = requests.get(signed_url, timeout=5)

#         original_file_path = testfiles[i]
#         with open(original_file_path, "rb") as original_file:
#             original_content = original_file.read()
#             assert downloaded_file.content == original_content, f"Downloaded file content does not match the original file content for file: {original_file_path}"

#     for file_tuple in files:
#         file_tuple[1].close()

def test_upload_invalid_file_extension(mocker):
    mocker.patch("src.main.minio_client.bucket_exists", return_value=True)
    files = [
        ("files", ("file1.txt", BytesIO(b"Text content"), "text/plain")),
    ]
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "type .txt not allowed" in response.json()["detail"]

def test_upload_mixed_valid_and_invalid_files():
    files = [("files", open(i, "rb")) for i in testfiles]
    invalid_file = ("files", ("invalid.txt", BytesIO(b"Invalid"), "text/plain"))
    files.append(invalid_file)
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "type .txt not allowed" in response.json()["detail"]

def test_upload_invalid_file_type(mocker):
    mocker.patch("src.main.minio_client.bucket_exists", return_value=True)
    files = [
        ("files", ("file1.pdf", BytesIO(b"Text content"), "application/pdf")),
    ]
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "type text/plain is not allowed" in response.json()["detail"]

def test_upload_file_exceeds_size_limit(mocker):
    mocker.patch("src.main.minio_client.bucket_exists", return_value=True)
    large_file_content = b"A" * (11 * 1024 * 1024)  # 11 MB
    files = [
        ("files", ("large_file.pdf", BytesIO(large_file_content), "application/pdf")),
    ]
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "size exceeds the limit" in response.json()["detail"]

def test_upload_no_files(mocker):
    mocker.patch("src.main.minio_client.bucket_exists", return_value=True)
    response = client.post("/upload", files=[])
    assert response.status_code == 400
    assert "No file uploaded" in response.json()["detail"]

def test_upload_internal_server_error(mocker):
    mocker.patch("src.main.minio_client.bucket_exists", return_value=True)
    mocker.patch("src.main.minio_client.put_object", side_effect=Exception("Minio error"))
    files = [
        ("files", open(CONAN3, "rb"))
    ]
    response = client.post("/upload", files=files)
    assert response.status_code == 500
    assert "Error uploading file" in response.json()["detail"]

def test_ocr_success(mocker):
    file_id = "test_file_id"
    mocker.patch("src.main.minio_client.stat_object", return_value=Mock(object_name=file_id))
    mocker.patch("src.main.simulate_ocr", return_value="Test content")
    mocker.patch("src.main.pc.list_indexes", return_value=Mock(names=lambda: [INDEX]))
    mocker.patch("src.main.pc.create_index")
    mocker.patch("src.main.PineconeVectorStore.from_documents")

    response = client.post(f"/ocr?file_id={file_id}")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "OCR processing and embedding upload completed."}

def test_ocr_file_not_found(mocker):
    file_id = "nonexistent_file_id"
    mocker.patch("src.main.minio_client.stat_object", side_effect=Exception("File not found"))
    response = client.post(f"/ocr?file_id={file_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == f"File not found: {file_id}"

def test_ocr_index_already_exists(mocker):
    file_id = "test_file_id"
    mocker.patch("src.main.minio_client.stat_object", return_value=Mock(object_name=file_id))
    mocker.patch("src.main.simulate_ocr", return_value="Test content")
    mocker.patch("src.main.pc.list_indexes", return_value=Mock(names=lambda: [file_id]))

    response = client.post(f"/ocr?file_id={file_id}")
    assert response.status_code == 400
    assert "index already exists" in response.json()["detail"]

def test_ocr_embedding_upload_error(mocker):
    file_id = "test_file_id"
    mocker.patch("src.main.minio_client.stat_object", return_value=Mock(object_name=file_id))
    mocker.patch("src.main.simulate_ocr", return_value="Test content")
    mocker.patch("src.main.pc.list_indexes", return_value=Mock(names=lambda: [INDEX]))
    mocker.patch("src.main.pc.create_index")
    mocker.patch("src.main.PineconeVectorStore.from_documents", side_effect=Exception("Embedding upload error"))
    response = client.post(f"/ocr?file_id={file_id}")
    assert response.status_code == 500
    assert "Error during OCR processing" in response.json()["detail"]

def test_extract_empty_query():
    query = "   "
    file_id = "test_file_id"
    response = client.post("/extract", params={"query": query, "file_id": file_id})
    assert response.status_code == 400
    assert "detail" in response.json()
    assert "Query cannot be empty or of only whitespace" in response.json()["detail"]

def test_extract_empty_file_id():
    query = "test_query"
    file_id = "     "
    response = client.post("/extract", params={"query": query, "file_id": file_id})
    assert response.status_code == 400
    assert "detail" in response.json()
    assert "File ID cannot be empty or of only whitespace" in response.json()["detail"]

def test_extract_missing_params():
    response = client.post("/extract", params={})
    assert response.status_code == 400
    assert "detail" in response.json()
    assert "File ID cannot be empty or of only whitespace" in response.json()["detail"]

def test_extract_internal_server_error(mocker):
    query = "What is the capital of France?"
    file_id = "test_file_id"
    mocker.patch("src.main.ChatOpenAI", side_effect=Exception("Mock exception"))
    mocker.patch("src.main.pc.list_indexes", return_value=Mock(names=lambda: [file_id]))
    response = client.post("/extract", params={"query": query, "file_id": file_id})
    assert response.status_code == 500
    assert "detail" in response.json()
    assert "Internal server error" in response.json()["detail"]
