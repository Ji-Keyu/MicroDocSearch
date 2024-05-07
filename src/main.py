from fastapi import FastAPI

app = FastAPI()

@app.post("/upload")
async def upload_files():
    return {"status": "success"}

@app.post("/ocr")
async def ocr_endpoint():
    return {"status": "success"}

@app.post("/extract")
async def extract_endpoint():
    return {"status": "success"}
