from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False
SCOTESE_VIEWER_ENABLED = os.environ.get("SCOTESE_VIEWER_ENABLED", "false").lower() == "true"
# Serving the original PALEOMAP JPEGs is a separate decision from running the viewer.
# The licence permits personal, teaching, research and scientific-publication use with
# credit, and names websites among the commercial uses needing the author's written
# consent, so this stays off unless that consent exists. The derived land fields are
# this project's own measurement and are governed by the same decision in spirit, which
# is why the attribution and the licence link stay on the page either way.
SCOTESE_SOURCE_MAPS_PUBLIC = os.environ.get(
    "SCOTESE_SOURCE_MAPS_PUBLIC", "false").lower() == "true"
SECRET_KEY = os.environ.get("SECRET_KEY", "")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("Production requires a random SECRET_KEY of at least 50 characters.")
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Production requires explicit ALLOWED_HOSTS.")
if not os.environ.get("DATABASE_PATH"):
    raise ImproperlyConfigured("Production requires DATABASE_PATH in a persistent DB directory.")

SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "true").lower() == "true"
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "true").lower() == "true"
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "86400"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "false").lower() == "true"
SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "false").lower() == "true"
# Enable only behind a proxy that strips client-supplied forwarding headers.
if os.environ.get("TRUST_PROXY_HEADERS", "false").lower() == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [u.strip() for u in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if u.strip()]

# WhiteNoise serves the collected static files from the image, so the host proxy only
# has to forward. Hashed names are deliberately not used: the module graph imports
# siblings by relative path, which a hashed name would break, and the templates already
# carry a version query.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
WHITENOISE_MAX_AGE = int(os.environ.get("WHITENOISE_MAX_AGE", "3600"))
