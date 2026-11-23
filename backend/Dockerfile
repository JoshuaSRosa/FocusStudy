FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# INSTALL_DEV=true also installs pytest (used by the compose "tests" service)
ARG INSTALL_DEV=false
COPY requirements.txt requirements-dev.txt ./
RUN if [ "$INSTALL_DEV" = "true" ]; then pip install --no-cache-dir -r requirements-dev.txt; \
    else pip install --no-cache-dir -r requirements.txt; fi

COPY . .

# The uploads folder must exist and belong to appuser BEFORE the volume is mounted
RUN useradd -m appuser && mkdir -p /app/uploads && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# App factory: gunicorn calls create_app() in each worker
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "main:create_app()"]
