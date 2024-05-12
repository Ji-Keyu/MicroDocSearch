import logging
import uuid
import os
import magic
import json
from typing import Dict
from datetime import timedelta
from fastapi import FastAPI, UploadFile, HTTPException, status
from typing import List
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

bucket_name = "uploads"
if not minio_client.bucket_exists(bucket_name):
    minio_client.make_bucket(bucket_name)

allowed_extensions = [".pdf", ".tiff", ".png", ".jpeg", ".jpg"]
allowed_mime_types = ["application/pdf", "image/tiff", "image/png", "image/jpeg"]
max_file_size = 10 * 1024 * 1024  # 10 MB
signed_url_ttl = 1 # hour

ocr_results = {
    "test1.pdf": json.load(open("./ocr/test1.json")),
    "test2.pdf": json.load(open("./ocr/test2.json")),
}

embeddings_model = "text-embedding-3-small"
chat_model = "gpt-3.5-turbo-0125"
temperature = 0
index_name = "microdocsearch"
ocr_file = "./ocr/test2.json"

pc = Pinecone()

@app.post("/upload")
async def upload_files(files: List[UploadFile] = []):
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
            # print(signed_url)
            uploaded_files.append({"file_id": file_id, "signed_url": signed_url})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

    return {"uploaded_files": uploaded_files}

def simulate_ocr(file_name: str):
    with open(ocr_file, "r") as file:
        data = json.load(file)
    content = data["analyzeResult"]["content"]
    return content

@app.post("/ocr")
async def ocr_endpoint(file_id: str):
    try:
        file_info = minio_client.stat_object(bucket_name, file_id)
        file_name = file_info.object_name
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found in storage: {file_id}")

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
        embeddings = OpenAIEmbeddings(model=embeddings_model)
        
        docs = text_splitter.create_documents([content])

        if index_name not in pc.list_indexes().names():
            raise HTTPException(status_code=500, detail=f"Index not found in Pinecone: {index_name}")
        
        PineconeVectorStore.from_documents(docs, embeddings, index_name=index_name)
        
        return {"status": "success", "message": "OCR processing and embedding upload completed."}
    
    except HTTPException as e:
        raise e
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during OCR processing: {str(e)}")

@app.post("/extract")
async def extract_endpoint(query: str) -> Dict[str, str]:
    """
    Extract relevant information from a given query using RAG, answer in natural language using OpenAI chat completion.

    Args:
        query (str): The question to search for and answer.

    Returns:
        Dict[str, str]: A dictionary containing the extracted response.

    Raises:
        ValueError: If the input query is empty or contains only whitespace.
    """
    if not query.strip():
        raise ValueError("Input query cannot be empty or contain only whitespace.")

    try:
        embeddings = OpenAIEmbeddings(model=embeddings_model)
        vectorstore = PineconeVectorStore(index_name=index_name, embedding=embeddings)
        retriever = vectorstore.as_retriever()
        prompt = hub.pull("rlm/rag-prompt")
        # You are an assistant for question-answering tasks. Use the following pieces of 
        # retrieved context to answer the question. If you don't know the answer, just say 
        # that you don't know. Use three sentences maximum and keep the answer concise.\n
        # Question: {question} \nContext: {context} \nAnswer:
        llm = ChatOpenAI(temperature=0, model=chat_model)
        rag_chain = (
            {"context": retriever , "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        response = rag_chain.invoke(query)
        logger.info(f"Extracted response: {response}")
        
        return {"response": response}
    
    except HTTPException as e:
        raise e
    
    except Exception as e:
        logger.exception(f"An error occurred at /extract: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@app.get("/health")
async def health_endpoint():
    return {"status": "success"}
