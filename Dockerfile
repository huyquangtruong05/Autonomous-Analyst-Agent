FROM python:3.10-slim
WORKDIR /app
RUN apt-get update -o Acquire::Retries=3 && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "src.backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]