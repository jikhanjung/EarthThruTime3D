"""Local reference globe catalogue; all asset paths come from the pinned manifest."""
import json
import math
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

# Control points the morph shader can hold at once. Every map has fewer named pieces
# than this, so the cap only ever trims the smallest.
MAX_MOTIONS = 16
# India crossed the Tethys at roughly 18 to 20 cm a year, about 2 degrees of arc per
# million years, and that is the fastest anyone measures. Pairs above it are reported,
# not dropped: the identity comes from a shared name, which is a stronger statement than
# a speed heuristic.
FASTEST_MEASURED_DEGREES_PER_MA = 2.0
# Below this a piece is an island on these maps, too small to carry a continent's morph.
MIN_MOTION_RADIUS_DEG = 4.0
# Two pieces whose mapped areas differ by more than this are not the same extent, so
# their centroids are not comparable. Antarctica is the clearest case: the maps draw it
# as a broken ice fringe, and the segmentation keeps a different share of it each time,
# which moves the centroid without anything having moved.
MAX_AREA_RATIO = 3.0


def derived_path(item, suffix):
    stem = Path(item["image"]["path"]).stem
    return settings.BASE_DIR / SEGMENTATION_DIR / f"{stem}-{suffix}"


def field_path(item):
    """Equirectangular signed-distance field: the form the viewer interpolates."""
    return derived_path(item, "field.png")


@lru_cache(maxsize=1)
def catalogue():
    return json.loads((settings.BASE_DIR / "sources/scotese-earth-history.json").read_text())


def enabled():
    return settings.SCOTESE_VIEWER_ENABLED


def piece_report(item):
    """The segmentation report's pieces for one map, or an empty list."""
    path = derived_path(item, "pieces.json")
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("pieces", [])


def landmass_names(pieces):
    return [{"name": name["name"], "lon": name["lon"], "lat": name["lat"]}
            for piece in pieces for name in piece.get("names", [])
            if name.get("display", True)]


def separation(first, second):
    """Great-circle separation in degrees between two [lon, lat] points."""
    lon1, lat1, lon2, lat2 = (math.radians(value) for value in (*first, *second))
    cosine = (math.sin(lat1) * math.sin(lat2)
              + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def _matched_pieces(older, newer):
    """One-to-one piece correspondences between two maps, by shared name.

    A piece that splits or merges across the gap has no single position to travel to,
    so those correspondences are dropped rather than read as motion.
    """
    def by_name(pieces):
        index = {}
        for position, piece in enumerate(pieces):
            for name in piece.get("names", []):
                index.setdefault(name.get("track") or name["name"], position)
        return index

    forward = by_name(older)
    backward = by_name(newer)
    links = {}
    for name, position in forward.items():
        if name in backward:
            links.setdefault(position, set()).add(backward[name])
    reverse = {}
    for source, targets in links.items():
        for target in targets:
            reverse.setdefault(target, set()).add(source)
    return [(older[source], newer[next(iter(targets))])
            for source, targets in links.items()
            if len(targets) == 1 and len(reverse[next(iter(targets))]) == 1]


def motions(frames, pieces_by_frame, limit=MAX_MOTIONS):
    """Per gap, how far each matched landmass travels, oldest gap first.

    Each entry carries a piece from where it sits on one map to where it sits on the
    next, so the viewer moves it and blends its outline on the way instead of
    dissolving the whole map into the following one.

    A shared identity is taken at its word however fast the implied motion is. India
    crossed the Tethys at around 18 to 20 centimetres a year, close to two degrees of
    arc per million years, so a speed limit tight enough to catch segmentation noise
    also throws away the best-known journey on these maps. Each entry reports the speed
    it implies, and `fast` marks the ones above the fastest plate anyone measures, so an
    implausible pairing stays visible instead of being silently dropped.

    What is dropped is measured rather than physical: a piece that split or merged, one
    too small to carry a morph, and one whose mapped area changed so much that the two
    centroids describe different extents of the same landmass.
    """
    result = []
    for older_frame, newer_frame in zip(frames, frames[1:]):
        span = abs(older_frame["age"] - newer_frame["age"])
        pairs = []
        for older, newer in _matched_pieces(pieces_by_frame[older_frame["id"]],
                                            pieces_by_frame[newer_frame["id"]]):
            radius = max(older.get("radius_deg", 0), newer.get("radius_deg", 0))
            if radius < MIN_MOTION_RADIUS_DEG:
                continue
            areas = (older.get("area_px", 0), newer.get("area_px", 0))
            if min(areas) <= 0 or max(areas) / min(areas) > MAX_AREA_RATIO:
                continue
            travelled = separation(older["centroid"], newer["centroid"])
            rate = travelled / span if span else 0.0
            pairs.append({"lon": older["centroid"][0], "lat": older["centroid"][1],
                          "to_lon": newer["centroid"][0], "to_lat": newer["centroid"][1],
                          "radius": round(radius, 3), "moved": round(travelled, 3),
                          "deg_per_ma": round(rate, 4),
                          "fast": rate > FASTEST_MEASURED_DEGREES_PER_MA})
        pairs.sort(key=lambda pair: pair["radius"], reverse=True)
        result.append(pairs[:limit])
    return result


def _first_allowed(values, choices, convert):
    for value in values:
        try:
            number = convert(value)
        except (TypeError, ValueError):
            continue
        if number in choices:
            return number
    return None


def sampling(request=None):
    """How to sample the timeline, from the settings with a per-request override.

    The query overrides exist so a density can be tried without a restart. Every path
    goes through the same allowlists, so none can hand the slider an odd range.
    """
    get = request.GET.get if request is not None else (lambda key: None)
    interval = _first_allowed((get("interval"), settings.SCOTESE_VIEWER_INTERVAL_MA),
                              settings.SCOTESE_VIEWER_INTERVAL_CHOICES, float)
    if interval is not None:
        return {"interval_ma": interval, "steps": None}
    count = _first_allowed((get("steps"), settings.SCOTESE_VIEWER_STEPS),
                           settings.SCOTESE_VIEWER_STEP_CHOICES, int)
    return {"interval_ma": None, "steps": 4 if count is None else count}


def _gap_for(ages, age):
    """Index of the older map of the pair that brackets `age`. Ages run oldest first."""
    for index in range(len(ages) - 1):
        if ages[index] >= age >= ages[index + 1]:
            return index
    return 0 if age > ages[0] else len(ages) - 2


def _stop(ages, age):
    index = _gap_for(ages, age)
    older, newer = ages[index], ages[index + 1]
    span = older - newer
    blend = 0.0 if span == 0 else (older - age) / span
    if blend >= 1.0:
        return [index + 1, index + 1, 0.0, round(newer, 4)]
    return [index, index + 1, round(blend, 5), round(age, 4)]


def timeline(frames, plan):
    """The slider's stops as [from frame, to frame, blend, age].

    Sending the stops rather than a rule lets the sampling change without the viewer
    knowing how it was produced, and lets an uneven grid, such as one stop per million
    years, sit beside the even one.
    """
    ages = [frame["age"] for frame in frames]
    if len(ages) < 2:
        return [[0, 0, 0.0, ages[0]]] if ages else []
    if plan["interval_ma"]:
        marks = set(ages)
        age = ages[0]
        while age > ages[-1]:
            age = max(ages[-1], age - plan["interval_ma"])
            marks.add(round(age, 4))
        return [_stop(ages, age) for age in sorted(marks, reverse=True)]
    stops = []
    for index in range(len(ages) - 1):
        for step in range(plan["steps"]):
            blend = step / plan["steps"]
            stops.append([index, index + 1, round(blend, 5),
                          round(ages[index] + (ages[index + 1] - ages[index]) * blend, 4)])
    stops.append([len(ages) - 1, len(ages) - 1, 0.0, ages[-1]])
    return stops


@require_safe
def globe(request):
    frames = []
    pieces_by_frame = {}
    if enabled():
        for item, korean in zip(catalogue()["maps"], KOREAN_LABELS):
            pieces_by_frame[item["id"]] = piece_report(item)
            frames.append({"id": item["id"], "label": korean, "title": item["image_label"],
                           "age": item["age_ma"], "bounds": BOUNDS[item["id"].removeprefix("scotese-")],
                           "url": reverse("globe-map", args=[item["id"]]),
                           "field": (reverse("globe-field", args=[item["id"]])
                                     if field_path(item).exists() else None),
                           "names": landmass_names(pieces_by_frame[item["id"]]),
                           "source": item["page"]["url"]})
    plan = sampling(request)
    return render(request, "core/home.html",
                  {"frames": frames, "viewer_enabled": enabled(),
                   "stops": timeline(frames, plan), "sampling": plan,
                   "motions": motions(frames, pieces_by_frame),
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
