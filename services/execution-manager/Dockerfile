FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY entrypoint.sh ./

# Install the base worker plus the optional OpenHands runtime extra so the
# coding agent can actually run (pulls litellm, boto3, anthropic, ...). The
# base package alone keeps the image lean for non-agent execution.
RUN pip install --no-cache-dir ".[runtime]" && chmod +x entrypoint.sh

EXPOSE 8001

ENTRYPOINT ["./entrypoint.sh"]