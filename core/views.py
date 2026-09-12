import logging
from django.conf import settings
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from config.version import VERSION
from core.globe import bundle_report

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
    bundle = bundle_report()
    served = not bundle["required"] or bundle["missing"] == 0
    if not served:
        logger.error("Derived land fields missing: %s", bundle["missing"])
    status = "ok" if ready and served else "unhealthy"
    if status == "ok" and settings.INTEGRITY_SENTINEL.exists():
        status = "degraded"
    return JsonResponse({"status": status, "version": VERSION,
                         "database": ready, "schema_ready": ready,
                         "fields": bundle},
                        status=200 if ready and served else 503)
