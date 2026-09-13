"""A single shared key that unlocks restricted datasets, entered where it is needed.

This is not authentication: there are no users, and anyone holding the key is the same
visitor as anyone else. It exists so a dataset whose licence does not permit publication
can still be looked at on a deployment, without putting it on the open web.

The site itself stays open. Only the resources that need the key ask for it, and the
grant is kept in the session so it is asked once.
"""
import hmac

from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

SESSION_FLAG = "access_granted"


def key():
    return getattr(settings, "ACCESS_KEY", "") or ""


def configured():
    return bool(key())


def granted(request):
    return request.session.get(SESSION_FLAG) is True


def unlock(request, offered):
    """Record the grant if the key matches. compare_digest keeps timing quiet."""
    if configured() and hmac.compare_digest(offered or "", key()):
        request.session[SESSION_FLAG] = True
        request.session.set_expiry(60 * 60 * 24 * 30)
        return True
    return False


def safe_next(value):
    """Only local paths, or the form becomes a way to send someone elsewhere."""
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return "/"


@require_http_methods(["GET", "POST"])
def gate(request):
    """Enter the key. Answers JSON when asked, so the viewer can unlock in place."""
    wants_json = request.headers.get("Accept", "").startswith("application/json")
    destination = safe_next(request.POST.get("next") or request.GET.get("next"))
    if request.method == "POST":
        opened = granted(request) or unlock(request, request.POST.get("key"))
        if wants_json:
            return JsonResponse({"granted": opened}, status=200 if opened else 401)
        if opened:
            return HttpResponseRedirect(destination)
        return render(request, "core/access.html",
                      {"wrong": True, "next": destination}, status=401)
    if wants_json:
        return JsonResponse({"granted": granted(request)})
    if granted(request) or not configured():
        return HttpResponseRedirect(destination)
    return render(request, "core/access.html", {"wrong": False, "next": destination})
