import json
from functools import lru_cache

from django.conf import settings

from config.version import APP_NAME, COPYRIGHT_YEAR, RELEASE_DATE, VENDOR, VERSION


@lru_cache(maxsize=1)
def plate_citations():
    """The citations the plate models' licences require, for pages outside the viewer."""
    directory = settings.BASE_DIR / "sources/plate-models"
    entries = []
    for path in sorted(directory.glob("*.json")):
        document = json.loads(path.read_text())
        entries.append({"citation": document["citation"],
                        "license": document["license"]["name"],
                        "license_url": document["license"]["url"],
                        "frame": document["reference_frame"]})
    return entries


def branding(request):
    return {"app_name": APP_NAME, "vendor": VENDOR, "version": VERSION,
            "release_date": RELEASE_DATE, "copyright_year": COPYRIGHT_YEAR,
            "plate_citations": plate_citations()}
