FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "fastapi==0.115.6" "uvicorn[standard]" "jinja2" "python-multipart" "mysql-connector-python" "httpx" "pandas" "openpyxl"

COPY api/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
