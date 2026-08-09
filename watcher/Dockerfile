FROM python:3.12-slim

ARG TESSERACT_PACKAGES="tesseract-ocr-deu tesseract-ocr-eng"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ocrmypdf \
    tesseract-ocr \
    ${TESSERACT_PACKAGES} \
    && rm -rf /var/lib/apt/lists/*

COPY watcher/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt


WORKDIR /opencloud-ocrmypdf

COPY watcher/watcher.py /opencloud-ocrmypdf/watcher.py

CMD ["python3","/opencloud-ocrmypdf/watcher.py"]
