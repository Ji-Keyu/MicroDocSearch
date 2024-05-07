FROM python:3.10-slim

# dependency
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# source
WORKDIR /app
COPY src src
WORKDIR /app/src

# start
# USER nonroot:nonroot
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
