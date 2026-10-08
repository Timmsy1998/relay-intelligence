FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=relay.settings
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml ./
COPY backend ./backend
COPY scripts ./scripts
RUN pip install --no-cache-dir --no-deps . && useradd --uid 10001 --create-home relay
USER relay
EXPOSE 8000
CMD ["gunicorn", "relay.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--timeout", "60"]
