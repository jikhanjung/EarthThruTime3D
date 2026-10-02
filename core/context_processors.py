import json
from functools import lru_cache

from django.conf import settings

from config.version import APP_NAME, APP_TITLE, COPYRIGHT_YEAR, RELEASE_DATE, VENDOR, VERSION


@lru_cache(maxsize=2)
def plate_citations(with_restricted=False):
    """The citations the plate models' licences require, for pages outside the viewer:
    the models this deployment may offer. A restricted one is cited only where a key
    exists to open it (the public site sets none)."""
    directory = settings.BASE_DIR / "sources/plate-models"
    entries = []
    for path in sorted(directory.glob("*.json")):
        document = json.loads(path.read_text())
        if not document.get("publish", True) and not with_restricted:
            continue
        entries.append({"citation": document["citation"],
                        "license": document["license"]["name"],
                        "license_url": document["license"]["url"],
                        "frame": document["reference_frame"]})
    return entries


def branding(request):
    keyed = bool(getattr(settings, "ACCESS_KEY", ""))
    return {"app_name": APP_NAME, "app_title": APP_TITLE, "vendor": VENDOR, "version": VERSION,
            "release_date": RELEASE_DATE, "copyright_year": COPYRIGHT_YEAR,
            "plate_citations": plate_citations(keyed), "access_key_enabled": keyed}
