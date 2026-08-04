FROM python:3.12-slim

ARG TESSERACT_PACKAGES="tesseract-ocr-deu tesseract-ocr-eng"

RUN apt update && apt install -y \
    ocrmypdf \
    tesseract-ocr \
    ${TESSERACT_PACKAGES} \
    curl \
    inotify-tools \
    && rm -rf /var/lib/apt/lists/*


RUN pip install \
    watchdog \
    requests \
    pyyaml


WORKDIR /opencloud-ocrmypdf

COPY watcher.py /opencloud-ocrmypdf/watcher.py

CMD ["python3","/opencloud-ocrmypdf/watcher.py"]