FROM python:3.10-slim

# dependency
RUN apt-get update && apt-get install -y libmagic1 curl
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# source
WORKDIR /app
COPY src src

# start
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
