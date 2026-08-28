FROM python:3.12-slim

# Tesseract is part of the ingest stage — scanned and faxed pages need
# word-level boxes, and the OCR confidence signal is what routes
# substantially handwritten pages to the manual-only queue.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
