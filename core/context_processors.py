import json
from functools import lru_cache

from django.conf import settings

from config.version import APP_NAME, COPYRIGHT_YEAR, RELEASE_DATE, VENDOR, VERSION


@lru_cache(maxsize=1)
def plate_citation():
    """The citation the plate model's licence requires, for pages outside the viewer."""
    path = settings.BASE_DIR / "sources/earthbyte-merdith2021.json"
    if not path.exists():
        return ""
    return json.loads(path.read_text())["citation"]


def branding(request):
    return {"app_name": APP_NAME, "vendor": VENDOR, "version": VERSION,
            "release_date": RELEASE_DATE, "copyright_year": COPYRIGHT_YEAR,
            "plate_citation": plate_citation()}
