from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = os.environ.get(  # noqa: F405
    "SECRET_KEY", "django-insecure-local-development-only-earththrutime3d"
)
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
