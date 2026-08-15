FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY packages /app/packages
COPY services /app/services
COPY apps /app/apps
COPY data /app/data
COPY scripts /app/scripts

EXPOSE 8000

CMD ["uvicorn", "services.coordinator.app:app", "--host", "0.0.0.0", "--port", "8000"]
