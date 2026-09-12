"""Local reference globe catalogue; all asset paths come from the pinned manifest."""
import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_safe

# Visually estimated ellipse extents [left, top, right, bottom] in source pixels.
# These are a preview calibration, not geodetic control points.
BOUNDS = {
    "650": [14, 36, 713, 386], "514": [14, 54, 708, 399],
    "458": [14, 40, 709, 390], "425": [14, 39, 708, 387],
    "390": [15, 37, 710, 384], "342": [16, 29, 710, 378],
    "306": [15, 37, 709, 385], "255": [14, 44, 706, 390],
    "237": [14, 44, 706, 392], "195": [14, 43, 709, 390],
    "152": [14, 42, 708, 389], "094": [14, 37, 708, 385],
    "066": [14, 46, 707, 393], "050": [13, 44, 706, 392],
    "014": [14, 39, 706, 388], "lgm": [14, 38, 706, 382],
    "000": [15, 41, 706, 387],
}
KOREAN_LABELS = ["후기 원생대", "후기 캄브리아기", "중기 오르도비스기", "중기 실루리아기",
                 "전기 데본기", "전기 석탄기", "후기 석탄기", "후기 페름기", "전기 트라이아스기",
                 "전기 쥐라기", "후기 쥐라기", "후기 백악기", "백악기 말 경계", "중기 에오세",
                 "중기 마이오세", "최후빙기극대기", "현재"]


# Derived land masks produced by scripts/segment_landmass.py. They are an
# interpretation of the published maps, not source data, and they are absent until
# that script has been run, so the viewer has to work without them.
SEGMENTATION_DIR = "data/derived/segmentation"


def derived_path(item, suffix):
    stem = Path(item["image"]["path"]).stem
    return settings.BASE_DIR / SEGMENTATION_DIR / f"{stem}-{suffix}"


def field_path(item):
    """Equirectangular signed-distance field: the form the viewer interpolates."""
    return derived_path(item, "field.png")


def landmass_names(item):
    """Names to print on the derived globe, one per named piece location.

    Read from the segmentation report rather than stored in the catalogue: the names
    belong to the pieces the segmentation found, and they move when it is rerun.
    """
    path = derived_path(item, "pieces.json")
    if not path.exists():
        return []
    report = json.loads(path.read_text())
    return [{"name": name["name"], "lon": name["lon"], "lat": name["lat"]}
            for piece in report.get("pieces", [])
            for name in piece.get("names", []) if name.get("display", True)]


@lru_cache(maxsize=1)
def catalogue():
    return json.loads((settings.BASE_DIR / "sources/scotese-earth-history.json").read_text())


def enabled():
    return settings.SCOTESE_VIEWER_ENABLED


@require_safe
def globe(request):
    frames = []
    if enabled():
        for item, korean in zip(catalogue()["maps"], KOREAN_LABELS):
            frames.append({"id": item["id"], "label": korean, "title": item["image_label"],
                           "age": item["age_ma"], "bounds": BOUNDS[item["id"].removeprefix("scotese-")],
                           "url": reverse("globe-map", args=[item["id"]]),
                           "field": (reverse("globe-field", args=[item["id"]])
                                     if field_path(item).exists() else None),
                           "names": landmass_names(item),
                           "source": item["page"]["url"]})
    return render(request, "core/home.html",
                  {"frames": frames, "viewer_enabled": enabled(),
                   "fields_available": any(frame["field"] for frame in frames)})


@require_safe
def source_map(request, map_id):
    if not enabled():
        raise Http404
    item = next((item for item in catalogue()["maps"] if item["id"] == map_id), None)
    if item is None:
        raise Http404
    try:
        file = (settings.BASE_DIR / item["image"]["path"]).open("rb")
    except FileNotFoundError:
        raise Http404("Local map not downloaded") from None
    response = FileResponse(file, content_type="image/jpeg")
    response["Cache-Control"] = "private, max-age=3600"
    return response


@require_safe
def land_field(request, map_id):
    if not enabled():
        raise Http404
    item = next((item for item in catalogue()["maps"] if item["id"] == map_id), None)
    if item is None:
        raise Http404
    try:
        file = field_path(item).open("rb")
    except FileNotFoundError:
        raise Http404("Land field not generated") from None
    response = FileResponse(file, content_type="image/png")
    response["Cache-Control"] = "private, max-age=3600"
    return response
