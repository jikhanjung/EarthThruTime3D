"""A single shared key, entered once, standing in for accounts.

This is not authentication: there are no users, and anyone holding the key is the same
visitor as anyone else. It exists so a deployment can be kept off the open web while one
person works on it, which is also what makes it acceptable to serve datasets whose
licences do not permit publication.

The key is compared in constant time and the grant is kept in the session, so it never
travels again after the first visit.
"""
import hmac

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

SESSION_FLAG = "access_granted"
# The health endpoint has to answer for the container's own check, and the static files
# carry nothing the key protects.
OPEN_PREFIXES = ("/healthz", "/static/")


def key():
    return getattr(settings, "ACCESS_KEY", "") or ""


def required():
    return bool(key())


def granted(request):
    return not required() or request.session.get(SESSION_FLAG) is True


class AccessKeyMiddleware:
    """Send anyone without the grant to the gate, keeping where they were headed."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not required() or granted(request):
            return self.get_response(request)
        path = request.path
        if path.startswith(OPEN_PREFIXES) or path == reverse("access-gate"):
            return self.get_response(request)
        return HttpResponseRedirect(f"{reverse('access-gate')}?next={path}")


@require_http_methods(["GET", "POST"])
def gate(request):
    if not required():
        return HttpResponseRedirect("/")
    destination = request.POST.get("next") or request.GET.get("next") or "/"
    if not destination.startswith("/") or destination.startswith("//"):
        destination = "/"
    if granted(request):
        return HttpResponseRedirect(destination)
    wrong = False
    if request.method == "POST":
        # compare_digest keeps a wrong key from being narrowed down by timing.
        if hmac.compare_digest(request.POST.get("key", ""), key()):
            request.session[SESSION_FLAG] = True
            request.session.set_expiry(60 * 60 * 24 * 30)
            return HttpResponseRedirect(destination)
        wrong = True
    return render(request, "core/access.html", {"wrong": wrong, "next": destination},
                  status=401 if wrong else 200)
