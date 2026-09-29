FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY docs ./docs
COPY web ./web
ENV PYTHONPATH=/app/src
ENV HOST=0.0.0.0
ENV PORT=8000
EXPOSE 8000
CMD ["python", "src/aslc/server.py"]
