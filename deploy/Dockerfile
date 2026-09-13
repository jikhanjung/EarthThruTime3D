FROM python:3.12-slim

ARG APP_VERSION=v0.5.0
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="EarthThruTime3D" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$VCS_REF

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    EARTHTHRUTIME_VERSION=$APP_VERSION \
    SCOTESE_DERIVED_DIR=/runtime/segmentation \
    PLATE_MODEL_DIR=/runtime/plates \
    DATABASE_PATH=/var/lib/earththrutime3d/db.sqlite3 \
    STATIC_ROOT=/app/staticfiles \
    MEDIA_ROOT=/app/media \
    ALLOWED_HOSTS=localhost,127.0.0.1
WORKDIR /app
COPY requirements.txt ./
COPY deploy/requirements.txt deploy/requirements.txt
RUN pip install --no-cache-dir -r deploy/requirements.txt \
    && groupadd --gid 10001 earth \
    && useradd --uid 10001 --gid 10001 --no-create-home earth
COPY config/ config/
COPY core/ core/
COPY templates/ templates/
COPY static/ static/
COPY sources/ sources/
COPY annotations/ annotations/
COPY deploy/ deploy/
COPY manage.py ./
# Collect at build time: the running container has a read-only root filesystem, and a
# build-time failure is better than a first-request one.
RUN SECRET_KEY=build-only-not-a-runtime-secret-000000000000000000000000000000 \
    ALLOWED_HOSTS=localhost SECURE_SSL_REDIRECT=false \
    python manage.py collectstatic --noinput \
    && SECRET_KEY=build-only-not-a-runtime-secret-000000000000000000000000000000 \
    ALLOWED_HOSTS=localhost python manage.py check \
    && mkdir -p /var/lib/earththrutime3d \
    && chown 10001:10001 /var/lib/earththrutime3d
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "/app/deploy/healthcheck.py"]
ENTRYPOINT ["sh", "/app/deploy/entrypoint.sh"]
