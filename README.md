MicroDocSearch
===

This repo implements a set of RESTful APIs that allows user to upload documents and search for relevant information using natural languages.

# Function
This repo accepts three endpoints for POST:
- `/upload`: accepts file uploads and returns a UUID. File formats are limited to pdf, tiff, png, and jpeg
- `/ocr`: takes the UUID of an uploaded file, ~~runs OCR~~, turns content into embeddings, and stores in a vector database. Returns status of success or failure
  - This endpoint does not really run OCR. The endpoint will simply pick up a local json as the file's content and process that.
- `/extract`: takes a query text and an UUID of an uploaded file, performs a vector search and returns matching attributes. 

# Getting Started
## Environment Variables
The repo by default uses `text-embedding-3-small` for embeddings and `gpt-3.5-turbo-0125` for chat completion, both from OpenAI.
The repo by default uses Pinecone as vector database, minio as blob storage.
To use API from OpenAI and Pinecone, their respective API keys are required.
```sh
cp .env_template .env
# place corresponding API keys in .env
```

## Start the services
Assuming Docker is already installed, the following commands will load the API keys environment variables, then build and start `minio` and `api` containers.
```
set -a && source .env && set +a
docker compose -f ./deployment/local/docker-compose.yml up --build
```
Since the `/ocr` is not really running OCR, one needs to prepare a `test.json` at `deployment/local/ocr/` as the OCR result.
The `test.json` should contain the OCR'ed content at `[analyzeResult][content]`.

# Examples
With a browser, go to `localhost:8000/docs` and use the built-in UI for FastAPI.
Without a browser, use `curl` to test manually.
Note that to use the presigned url returned, one needs to add the following lines to `/etc/hosts`
```
127.0.0.1 host.docker.internal
127.0.0.1 gateway.docker.internal
```

# Future consideration
- Custom bucket at `/upload`
- Custom index at `/ocr` and `/extract`
- Spin up multiple minio instances for redundancy
- Use nginx
