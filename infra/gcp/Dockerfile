FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=relay.settings
WORKDIR /app
COPY requirements-gcp.lock ./
RUN pip install --no-cache-dir -r requirements-gcp.lock
COPY pyproject.toml ./
COPY backend ./backend
COPY scripts ./scripts
RUN pip install --no-cache-dir --no-deps . && useradd --uid 10001 --create-home relay
USER relay
# Cloud Run is configured with port 8000.
EXPOSE 8000
CMD ["gunicorn", "relay.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60"]
