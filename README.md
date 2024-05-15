MicroDocSearch
===

This repo implements a set of APIs that allows user to upload documents and search for relevant information using natural languages. The documents and query don't need to be of the same language.

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
- `/upload`
```bash
$ curl -X POST -F "files=@./static/conan13.jpg" http://localhost:8000/upload
{"uploaded_files":[{"file_id":"037f43c8-0a80-4430-aa1d-1254c0ff5b93","signed_url":"http://host.docker.internal:9000/uploads/037f43c8-0a80-4430-aa1d-1254c0ff5b93?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=minioadmin%2F20240514%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20240514T225202Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=83c1d0f9748a63d8a1e4eca448650b61da1a90f6ef0d500d4a0ce2a87f092478"}]}
```
The minio console should show the file uploaded.
Note that to use the presigned url returned, one needs to add the following lines to `/etc/hosts`
```
127.0.0.1 host.docker.internal
127.0.0.1 gateway.docker.internal
```
- `/ocr`
```bash
$ curl -X POST "http://localhost:8000/ocr?file_id=037f43c8-0a80-4430-aa1d-1254c0ff5b93" # might take a while
{"status":"success","message":"OCR processing and embedding upload completed."}
```
The Pinecone page should now show the vectors stored.
- `/extract`
```bash
$ curl -X 'POST' \
  'http://localhost:8000/extract?file_id=037f43c8-0a80-4430-aa1d-1254c0ff5b93&query=what%27s%20the%20height%20limit%20of%20building%20construction' \
  -H 'accept: application/json' \
  -d ''
{"response":"The height limit for building construction is when the building's height exceeds thirty-one meters. In such cases, special evacuation staircases must be provided for certain floors. The specific requirements for these staircases are outlined in the regulations."}
```

# Future consideration
- Refined doc content splitting design according to purpose
  - For instance, for regulation documents specifically, can split content according to each individual rule
- Custom bucket at `/upload`
- Spin up multiple minio instances for redundancy
- Use nginx
