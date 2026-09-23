# --- build the dashboard ---
FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- runtime: API + dashboard + pipeline CLI ---
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PORT=8000
COPY requirements.txt ./
# Optional build secret for networks that inspect HTTPS (e.g. NetFree): an extra CA bundle
# used only by pip during this step - never stored in the image. Cloud builds don't pass it.
#   docker build --secret id=extra_ca,src=path/to/ca.pem .
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then \
        cat /etc/ssl/certs/ca-certificates.crt /run/secrets/extra_ca > /tmp/ca-bundle.pem; \
        export PIP_CERT=/tmp/ca-bundle.pem; \
    fi; \
    pip install --no-cache-dir -r requirements.txt && rm -f /tmp/ca-bundle.pem
COPY alembic.ini ./
COPY backend/ backend/
COPY config/ config/
COPY fixtures/ fixtures/
COPY --from=frontend /app/frontend/dist frontend/dist

# Never run as root in production.
RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

EXPOSE 8000
# Hosting platforms assign the port via $PORT and terminate HTTPS in a proxy in front of us;
# --proxy-headers makes the app see the real scheme/client. Migrations run on every start
# (Alembic is idempotent), so a new release upgrades the schema before serving.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
