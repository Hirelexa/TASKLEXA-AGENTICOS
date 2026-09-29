FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

COPY apps/api/pyproject.toml ./pyproject.toml
COPY apps/api/src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "tasklexa_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

