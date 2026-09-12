#!/bin/sh
# Startup order matters: check the configuration, bring the schema up to date in the
# persistent volume, prove the runtime bundle is the one this image expects, then serve.
set -eu
python manage.py check
python manage.py migrate --noinput
python /app/deploy/verify_bundle.py
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-2}" --worker-class gthread --threads "${GUNICORN_THREADS:-4}" \
    --timeout 60 --max-requests 1000 --max-requests-jitter 100 \
    --worker-tmp-dir /tmp --access-logfile - --error-logfile -
