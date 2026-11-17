FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# libzbar0        -> pyzbar (QR decode)
# tesseract-ocr   -> pytesseract (OCR engine + English traineddata)
# tesseract-ocr-hin -> Hindi traineddata, for the Tier 3 Hindi OCR stretch goal
# libglib2.0-0    -> opencv-python-headless
# libgl1 is deliberately NOT installed: only the headless OpenCV build is used,
# which does not link libGL. It would be needed by opencv-contrib-python, which
# nothing may pull in (see the OCR engine decision in CLAUDE.md).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libzbar0 \
        tesseract-ocr \
        tesseract-ocr-hin \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN mkdir -p /data/uploads /keys

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
