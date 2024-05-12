MicroDocSearch
===

This repo implements a set of RESTful APIs that allows user to upload documents and search for relevant information using natural languages.

# Function
This repo accepts three endpoints for POST:
- `/upload`: accepts file uploads and returns a UUID. File formats are limited to pdf, tiff, png, and jpeg
- `/ocr`: takes the UUID of an uploaded file, runs OCR, turns to embeddings, and stores in a vector database. Returns status of success or failure
- `/extract`: takes a query text and an UUID of an uploaded file, performs a vector search and returns matching attributes. 

# Getting Started
The repo by default uses `text-embedding-3-small` for embeddings and `gpt-3.5-turbo-0125` for chat completion, both from OpenAI. 
```sh
cp .env_template .env
# place corresponding API keys in .env
set -a && source .env && set +a
docker compose -f ./deployment/local/docker-compose.yml up --build
```

# Examples


# Future consideration
- Custom index at `/ocr` and `/extract`
