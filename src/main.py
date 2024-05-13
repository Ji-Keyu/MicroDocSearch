"""
This module provides three endpoints to
upload file, store contents' embeddings, and retrieve file content based on query
"""

import logging
import uuid
import os
import json
from typing import Dict, List
from datetime import timedelta
import magic
from fastapi import FastAPI, UploadFile, HTTPException, File, Query
from minio import Minio
from pinecone import Pinecone
from langchain import hub
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

minio_client = Minio(
    os.getenv("MINIO_ENDPOINT", "host.docker.internal:9000"),
    access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
    secure=False,
)

BUCKET = "uploads"

allowed_extensions = [".pdf", ".tiff", ".png", ".jpeg", ".jpg"]
allowed_mime_types = ["application/pdf", "image/tiff", "image/png", "image/jpeg"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
TTL = 1 # hour

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-3.5-turbo-0125"
TEMP = 0
INDEX = "microdocsearch"
OCR_FILE = "./ocr/test2.json"

pc = Pinecone()

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(None)):
    """
    Store uploaded file

    Args:
        files (List[UploadFile]): The files being uploaded

    Returns:
        {"uploaded_files": uploaded_files}
        Uploaded_files is list of Dict containing "file_id" and "signed_url"
    """
    if not files:
        raise HTTPException(status_code=400, detail="No file uploaded")

    uploaded_files = []

    if not minio_client.bucket_exists(BUCKET):
        minio_client.make_bucket(BUCKET)

    for file in files:
        if file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400,
                                detail=f"File size exceeds the limit of {MAX_FILE_SIZE} bytes.")

        _, file_extension = os.path.splitext(file.filename.lower())
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"File type {file_extension} not allowed.")

        file_header = await file.read(2048)
        file_type = magic.from_buffer(file_header, mime=True)
        if file_type not in allowed_mime_types:
            raise HTTPException(status_code=400, detail=f"File type {file_type} is not allowed.")
        file.file.seek(0)

        file_id = str(uuid.uuid4())

        try:
            minio_client.put_object(
                bucket_name=BUCKET,
                object_name=file_id,
                data=file.file,
                length=file.size,
                content_type=file.content_type
            )
            signed_url = minio_client.presigned_get_object(BUCKET, file_id, timedelta(hours=TTL))
            # print(signed_url)
            uploaded_files.append({"file_id": file_id, "signed_url": signed_url})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}") from e

    return {"uploaded_files": uploaded_files}

def simulate_ocr(_: str):
    """
    Simulate OCR

    Args:
        file_id (str): The id of file to process

    Returns:
        prepared OCR result stored locally
    """
    with open(OCR_FILE, "r", encoding='utf-8') as file:
        data = json.load(file)
    content = data["analyzeResult"]["content"]
    return content

@app.post("/ocr")
async def ocr_endpoint(file_id: str):
    """
    Run OCR on specified file, turn into embeddings, and store in Pinecone db

    Args:
        file_id (str): The id of file to process

    Returns:
        {"status": "success", "message": "OCR processing and embedding upload completed."}
    """
    try:
        file_info = minio_client.stat_object(BUCKET, file_id)
        file_name = file_info.object_name
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}") from e

    content = simulate_ocr(file_name)

    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=[
                "\n\n",
                "\n",
                " ",
                ".",
                ",",
                "\u200b",  # Zero-width space
                "\uff0c",  # Fullwidth comma
                "\u3001",  # Ideographic comma
                "\uff0e",  # Fullwidth full stop
                "\u3002",  # Ideographic full stop
                "",
            ],)
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

        docs = text_splitter.create_documents([content])

        if INDEX not in pc.list_indexes().names():
            raise HTTPException(status_code=500, detail=f"Index not found in db: {INDEX}")

        PineconeVectorStore.from_documents(docs, embeddings, index_name=INDEX)

        return {"status": "success", "message": "OCR processing and embedding upload completed."}

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during OCR processing: {str(e)}") from e

@app.post("/extract")
async def extract_endpoint(query: str = Query("", min_length=1)) -> Dict[str, str]:
    """
    Extract relevant information from a given query using RAG

    Args:
        query (str): The question to search for and answer.

    Returns:
        Dict[str, str]: A dictionary containing the extracted response.
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty or of only whitespace.")

    try:
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        vectorstore = PineconeVectorStore(index_name=INDEX, embedding=embeddings)
        retriever = vectorstore.as_retriever()
        prompt = hub.pull("rlm/rag-prompt")
        # You are an assistant for question-answering tasks. Use the following pieces of
        # retrieved context to answer the question. If you don't know the answer, just say
        # that you don't know. Use three sentences maximum and keep the answer concise.\n
        # Question: {question} \nContext: {context} \nAnswer:
        llm = ChatOpenAI(temperature=TEMP, model=CHAT_MODEL)
        rag_chain = (
            {"context": retriever , "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        response = rag_chain.invoke(query)
        logger.info("Extracted response: %s", response)

        return {"response": response}

    except HTTPException as e:
        raise e

    except Exception as e:
        logger.exception("An error occurred at /extract: %s", str(e))
        raise HTTPException(status_code=500, detail="An internal server error occurred.") from e

@app.get("/health")
async def health_endpoint():
    """
    Health check endpoint

    Returns:
        {"status": "success"}

    """
    return {"status": "success"}
