FROM python:3.12.16-slim-bookworm

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY reports/results.json ./reports/results.json
ENV PYTHONPATH=/app/src
USER 65532:65532
EXPOSE 8000
CMD ["python", "-m", "storage_observatory.metrics_service", "--results", "reports/results.json", "--port", "8000"]

