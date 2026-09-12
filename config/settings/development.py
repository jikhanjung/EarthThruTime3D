from .base import *  # noqa: F403

DEBUG = True
SCOTESE_VIEWER_ENABLED = True
SCOTESE_SOURCE_MAPS_PUBLIC = True
SECRET_KEY = os.environ.get(  # noqa: F405
    "SECRET_KEY", "django-insecure-local-development-only-earththrutime3d"
)
# Tailnet access for local review: ".ts.net" covers MagicDNS names; add tailnet
# IPs or other hosts with DEV_ALLOWED_HOSTS (comma separated).
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", ".ts.net"] + [
    h.strip() for h in os.environ.get("DEV_ALLOWED_HOSTS", "").split(",") if h.strip()  # noqa: F405
]
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
