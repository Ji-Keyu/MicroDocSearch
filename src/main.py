from datetime import timedelta
from fastapi import FastAPI, UploadFile, HTTPException, status
from typing import List
from minio import Minio
import uuid
import os
import magic

app = FastAPI()

minio_client = Minio(
    os.getenv("MINIO_ENDPOINT", "host.docker.internal:9000"),
    access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
    secure=False,
)

bucket_name = "uploads"
if not minio_client.bucket_exists(bucket_name):
    minio_client.make_bucket(bucket_name)

allowed_extensions = [".pdf", ".tiff", ".png", ".jpeg", ".jpg"]
allowed_mime_types = ["application/pdf", "image/tiff", "image/png", "image/jpeg"]
max_file_size = 10 * 1024 * 1024  # 10 MB
signed_url_ttl = 1 # hour

@app.post("/upload")
async def upload_files(files: List[UploadFile]):
    uploaded_files = []

    for file in files:
        if file.size > max_file_size:
            raise HTTPException(status_code=400, detail=f"File size exceeds the maximum limit of {max_file_size} bytes.")
        
        _, file_extension = os.path.splitext(file.filename.lower())
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"File type {file_extension} is not allowed.")
        
        file_header = await file.read(2048)
        file_type = magic.from_buffer(file_header, mime=True)
        if file_type not in allowed_mime_types:
            raise HTTPException(status_code=400, detail=f"File type {file_type} is not allowed.")
        file.file.seek(0)

        file_id = str(uuid.uuid4())

        try:
            minio_client.put_object(
                bucket_name=bucket_name,
                object_name=file_id,
                data=file.file,
                length=file.size,
                content_type=file.content_type
            )
            signed_url = minio_client.presigned_get_object(bucket_name, file_id, expires=timedelta(hours=signed_url_ttl))
            print(signed_url)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

        uploaded_files.append({"file_id": file_id, "signed_url": signed_url})
        return {"uploaded_files": uploaded_files}


@app.post("/ocr")
async def ocr_endpoint():
    return {"status": "success"}

@app.post("/extract")
async def extract_endpoint():
    return {"status": "success"}

@app.get("/health")
async def health_endpoint():
    return {"status": "success"}
