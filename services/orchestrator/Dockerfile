FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY entrypoint.sh ./

RUN pip install --no-cache-dir ".[temporal]" && chmod +x entrypoint.sh

EXPOSE 8002

ENTRYPOINT ["./entrypoint.sh"]