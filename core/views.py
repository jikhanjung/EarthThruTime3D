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


@require_safe
def language(request, code):
    """Remember a language choice in the cookie LocaleMiddleware reads, then go back."""
    from django.http import Http404, HttpResponseRedirect
    from django.utils import translation
    from core.access import safe_next
    if code not in dict(settings.LANGUAGES):
        raise Http404
    response = HttpResponseRedirect(safe_next(request.GET.get("next")))
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, code, max_age=365 * 24 * 3600,
                        samesite="Lax")
    translation.activate(code)
    return response
