import logging
from django.conf import settings
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from config.version import VERSION

logger = logging.getLogger(__name__)


@never_cache
@require_safe
def healthz(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM django_migrations LIMIT 1")
            ready = cursor.fetchone() is not None
    except DatabaseError:
        logger.exception("Health database check failed")
        ready = False
    status = "ok" if ready else "unhealthy"
    if ready and settings.INTEGRITY_SENTINEL.exists():
        status = "degraded"
    return JsonResponse({"status": status, "version": VERSION,
                         "database": ready, "schema_ready": ready},
                        status=200 if ready else 503)
