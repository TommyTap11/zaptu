FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
# Install runtime deps only (drop pytest from the image)
RUN pip install --no-cache-dir $(grep -vE '^(pytest|pytest-asyncio)' requirements.txt)

COPY src ./src
COPY web ./web
COPY data ./data

ENV PYTHONPATH=src
ENV HOST=0.0.0.0
ENV PORT=8000
ENV ZAPTU_DATA_DIR=./data
ENV ZAPTU_MOCK_FORWARDER=0

EXPOSE 8000
CMD ["python", "src/aslc/server.py"]
