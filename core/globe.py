"""Local reference globe catalogue; all asset paths come from the pinned manifest."""
import json
import math
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_safe

from core.access import configured as access_key_configured
from core.access import granted as access_granted

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
# Two sources of land masks. The 2016 PaleoAtlas is the default: it is the same edition as
# the PALEOMAP rotation model, so its coastlines and that model's plates agree. The 2002
# web maps stay available for comparison. Each source is a catalogue plus the directory
# its derived fields are read from.
MASK_SOURCES = {
    "paleoatlas2016": {"catalogue": "sources/paleomap-atlas-2016.json",
                       "directory": "PALEOATLAS_DERIVED_DIR",
                       "title": "PALEOMAP PaleoAtlas (2016)"},
    "scotese2002": {"catalogue": "sources/scotese-earth-history.json",
                    "directory": "SCOTESE_DERIVED_DIR",
                    "title": "Scotese PALEOMAP 웹 지도 (2002)"},
}
DEFAULT_MASK_SOURCE = "paleoatlas2016"

# Korean labels for the 2016 maps, derived from each map's age with the boundaries of the
# ICS International Chronostratigraphic Chart (v2023/09). The age decides the label, so a
# stage name in a file name that disagrees with its age does not carry over. Each entry is
# the age a label runs up to, exclusive.
PERIODS = [
    (0.0117, "홀로세"), (2.58, "플라이스토세"), (5.333, "플라이오세"), (23.03, "마이오세"), (33.9, "올리고세"),
    (56.0, "에오세"), (66.0, "팔레오세"), (100.5, "후기 백악기"), (145.0, "전기 백악기"),
    (161.5, "후기 쥐라기"), (174.7, "중기 쥐라기"), (201.4, "전기 쥐라기"),
    (237.0, "후기 트라이아스기"), (247.2, "중기 트라이아스기"), (251.902, "전기 트라이아스기"),
    (259.51, "후기 페름기"), (273.01, "중기 페름기"), (298.9, "전기 페름기"),
    (323.2, "후기 석탄기"), (358.9, "전기 석탄기"), (382.7, "후기 데본기"), (393.3, "중기 데본기"),
    (419.2, "전기 데본기"), (427.4, "후기 실루리아기"), (433.4, "중기 실루리아기"),
    (443.8, "전기 실루리아기"), (458.4, "후기 오르도비스기"), (470.0, "중기 오르도비스기"),
    (485.4, "전기 오르도비스기"), (497.0, "후기 캄브리아기"), (506.5, "중기 캄브리아기"),
    (538.8, "전기 캄브리아기"), (635.0, "에디아카라기"), (720.0, "크라이오제니아기"),
    (1000.0, "토니아기"),
]


def period_label(item):
    """Korean label for a 2016 atlas map, from its age alone."""
    if item["id"].endswith("-lgm"):
        return "최후빙기 최성기"
    if item["age_ma"] == 0:
        return "현재"
    for upper, label in PERIODS:
        if item["age_ma"] < upper:
            return label
    return "원생대"


KOREAN_LABELS = ["후기 원생대", "후기 캄브리아기", "중기 오르도비스기", "중기 실루리아기",
                 "전기 데본기", "전기 석탄기", "후기 석탄기", "후기 페름기", "전기 트라이아스기",
                 "전기 쥐라기", "후기 쥐라기", "후기 백악기", "백악기 말 경계", "중기 에오세",
                 "중기 마이오세", "최후빙기극대기", "현재"]


# Derived land masks produced by scripts/segment_landmass.py (2002 maps) and
# scripts/segment_paleoatlas.py (2016 atlas). They are an
# interpretation of the published maps, not source data, and they are absent until
# that script has been run, so the viewer has to work without them.

# Control points the morph shader can hold at once. Every map has fewer named pieces
# than this, so the cap only ever trims the smallest.
MAX_MOTIONS = 16
# Spacing for the stops older than any map. Coarse on purpose: there is no surface to
# morph there, only a reconstruction to turn.
DEEP_STEP_MA = 25.0
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


def source_of(item):
    """Which mask source a catalogue entry belongs to: 2002 entries carry an image."""
    return "scotese2002" if "image" in item else "paleoatlas2016"


def derived_path(item, suffix):
    source = source_of(item)
    stem = Path(item["image"]["path"]).stem if source == "scotese2002" else item["id"]
    directory = getattr(settings, MASK_SOURCES[source]["directory"])
    return Path(directory) / f"{stem}-{suffix}"


def field_path(item):
    """Equirectangular signed-distance field: the form the viewer interpolates."""
    return derived_path(item, "field.png")


@lru_cache(maxsize=4)
def catalogue(source="scotese2002"):
    return json.loads((settings.BASE_DIR / MASK_SOURCES[source]["catalogue"]).read_text())


def mask_source(request=None):
    """The mask source to show: a per-request comparison override, then the setting."""
    asked = request.GET.get("masks") if request is not None else None
    for value in (asked, getattr(settings, "MASK_SOURCE", DEFAULT_MASK_SOURCE)):
        if value in MASK_SOURCES:
            return value
    return DEFAULT_MASK_SOURCE


def find_map(map_id):
    """A catalogue entry by id, from whichever source has it."""
    for source in MASK_SOURCES:
        item = next((item for item in catalogue(source)["maps"] if item["id"] == map_id), None)
        if item is not None:
            return item
    return None


def enabled():
    return settings.SCOTESE_VIEWER_ENABLED


def source_maps_public():
    """Whether the original PALEOMAP JPEGs are served to visitors.

    Separate from running the viewer. The licence names websites among the commercial
    uses needing the author's written consent, so a deployment can show the derived
    land fields, which are this project's own measurement, while keeping the published
    maps off the network. The attribution and the licence link stay either way.
    """
    return getattr(settings, "SCOTESE_SOURCE_MAPS_PUBLIC", False)


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


def atlas_motions(frames):
    """Per gap, the 2016 landmasses carried by the PALEOMAP rotations, oldest gap first.

    scripts/atlas_motions.py writes these from the rotation model, so nothing is matched
    here. The file has to describe exactly these frames in this order; anything else is
    ignored rather than applied to the wrong gap, and the maps then blend in place.
    """
    path = Path(settings.PALEOATLAS_DERIVED_DIR) / "motions.json"
    if not path.exists():
        return []
    gaps = json.loads(path.read_text()).get("gaps", [])
    expected = list(zip((frame["id"] for frame in frames), (frame["id"] for frame in frames[1:])))
    if [(gap["from"], gap["to"]) for gap in gaps] != expected:
        return []
    return [gap["pairs"][:MAX_MOTIONS] for gap in gaps]


def coastline_index():
    path = Path(settings.PALEOCOASTLINES_DERIVED_DIR) / "index.json"
    return json.loads(path.read_text()) if path.exists() else None


def coastlines(source):
    """The fossil-checked PaleoCoastlines layer for the page, where it applies.

    Offered only over the 2016 masks: both are PALEOMAP, so the lines sit on the masks with
    no rotation (devlog 026). Over the 2002 maps, whose longitudes drift from that frame,
    the same lines would look like a disagreement they are not.
    """
    index = coastline_index()
    if source != "paleoatlas2016" or not index:
        return None
    return {"title": index["title"], "citation": index["citation"],
            "license": index["license"], "license_url": index["license_url"],
            "ages": [{"age": entry["age_ma"],
                      "url": reverse("globe-coastline", args=[int(entry["age_ma"])])}
                     for entry in index["ages"]]}


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


SAMPLING_OPTIONS = [("steps:4", "지도마다 4단계"), ("interval:1", "1 Myr"),
                    ("interval:5", "5 Myr"), ("interval:10", "10 Myr")]


def sampling_choice(plan):
    """The timeline control's value for a plan, and the options it offers."""
    if plan["interval_ma"]:
        choice, label = f"interval:{plan['interval_ma']:g}", f"{plan['interval_ma']:g} Myr"
    else:
        choice, label = f"steps:{plan['steps']}", f"지도마다 {plan['steps']}단계"
    options = list(SAMPLING_OPTIONS)
    if choice not in dict(options):
        options.append((choice, label))
    return choice, options


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


def deep_stops(oldest_map, deepest_model, step=DEEP_STEP_MA):
    """Stops older than any map, where only a plate model has anything to say.

    The published maps stop at 650 Ma but two of the plate models reach 1000 and one
    reaches 1800. Rather than pretend the surface is unknown there, these stops carry no
    map at all: the viewer paints bare ocean and draws the reconstruction over it, and
    says as much. A map frame index of -1 is what marks them.
    """
    if not deepest_model or deepest_model <= oldest_map + step:
        return []
    stops = []
    age = deepest_model
    while age > oldest_map + step / 2:
        stops.append([-1, -1, 0.0, round(age, 4)])
        age -= step
    return stops


def timeline(frames, plan, deepest_model=None):
    """The slider's stops as [from frame, to frame, blend, age].

    Sending the stops rather than a rule lets the sampling change without the viewer
    knowing how it was produced, and lets an uneven grid, such as one stop per million
    years, sit beside the even one.
    """
    ages = [frame["age"] for frame in frames]
    if len(ages) < 2:
        return [[0, 0, 0.0, ages[0]]] if ages else []
    deep = deep_stops(ages[0], deepest_model)
    if plan["interval_ma"]:
        marks = set(ages)
        age = ages[0]
        while age > ages[-1]:
            age = max(ages[-1], age - plan["interval_ma"])
            marks.add(round(age, 4))
        return deep + [_stop(ages, age) for age in sorted(marks, reverse=True)]
    stops = []
    for index in range(len(ages) - 1):
        for step in range(plan["steps"]):
            blend = step / plan["steps"]
            stops.append([index, index + 1, round(blend, 5),
                          round(ages[index] + (ages[index + 1] - ages[index]) * blend, 4)])
    stops.append([len(ages) - 1, len(ages) - 1, 0.0, ages[-1]])
    return deep + stops


# Plate models are served whole rather than per map: each is one model, and the viewer
# reconstructs from it at whatever time the reader has chosen. Only these three names
# are reachable, under a model id that must match a manifest.
PLATE_LAYERS = ("rotations", "continents", "coastlines")
PLATE_MANIFESTS = "sources/plate-models"


def plate_manifests():
    return sorted((settings.BASE_DIR / PLATE_MANIFESTS).glob("*.json"))


def plate_path(model, layer):
    return Path(settings.PLATE_MODEL_DIR) / model / f"{layer}.json"


def restricted(document):
    """Whether this model needs the shared key before it may be handed over."""
    return not document.get("publish", True)


def offerable(document):
    """A restricted model is listed only where a key exists to unlock it."""
    return not restricted(document) or access_key_configured()


def plate_models(request=None):
    """Every packed plate model this deployment may offer, with its attribution.

    Attribution travels with the URLs because each model carries its own licence and
    because a reader has to be able to tell which dataset a line came from.
    """
    available = []
    for path in plate_manifests():
        document = json.loads(path.read_text())
        model = document["id"]
        if not offerable(document):
            continue
        if not all(plate_path(model, layer).exists() for layer in ("rotations", "continents")):
            continue
        available.append({
            "id": model,
            "preferred": bool(document.get("preferred")),
            "published": not restricted(document),
            "locked": restricted(document) and not access_granted(request),
            "title": document["short_title"],
            "short": document.get("menu_title", document["short_title"]),
            "frame": document["reference_frame"],
            "covers": document["covers_ma"],
            "citation": document["citation"],
            "license": document["license"]["name"],
            "license_url": document["license"]["url"],
            "limitations": document["limitations"],
            "note": document.get("relationship", ""),
            "layers": {layer: reverse("plate-file", args=[model, layer])
                       for layer in PLATE_LAYERS if plate_path(model, layer).exists()},
        })
    # The manifest says which model to open with; the rest follow by title.
    available.sort(key=lambda entry: (not entry["preferred"], entry["title"]))
    return available


def bundle_report():
    """Whether the derived land fields this deployment serves are actually present.

    A viewer that is switched on but has no fields is broken rather than degraded, so
    the health endpoint fails on it: the container will have been started against the
    wrong runtime bundle.
    """
    if not enabled():
        return {"required": False, "expected": 0, "missing": 0}
    source = mask_source()
    maps = catalogue(source)["maps"]
    missing = [item["id"] for item in maps if not field_path(item).exists()]
    return {"required": True, "source": source, "expected": len(maps),
            "missing": len(missing), "missing_ids": missing[:5]}


@require_safe
def globe(request):
    frames = []
    pieces_by_frame = {}
    source = mask_source(request)
    if enabled():
        document = catalogue(source)
        if source == "scotese2002":
            entries = [(item, korean, item["image_label"],
                        BOUNDS[item["id"].removeprefix("scotese-")],
                        reverse("globe-map", args=[item["id"]]) if source_maps_public() else None,
                        item["page"]["url"])
                       for item, korean in zip(document["maps"], KOREAN_LABELS)]
        else:
            # The 2016 rasters are never served, published or not: their licence is not
            # yet confirmed, so only the fields derived from them reach the page.
            entries = [(item, period_label(item), item["label"], None, None,
                        document["license"]["source"]) for item in document["maps"]]
        for item, korean, title, bounds, url, link in entries:
            pieces_by_frame[item["id"]] = piece_report(item)
            frames.append({"id": item["id"], "label": korean, "title": title,
                           "age": item["age_ma"], "bounds": bounds, "url": url,
                           "field": (reverse("globe-field", args=[item["id"]])
                                     if field_path(item).exists() else None),
                           "names": landmass_names(pieces_by_frame[item["id"]]),
                           "source": link})
    plan = sampling(request)
    models = plate_models(request)
    deepest = max((model["covers"][1] for model in models), default=None)
    return render(request, "core/home.html",
                  {"frames": frames, "viewer_enabled": enabled(),
                   "stops": timeline(frames, plan, deepest), "sampling": plan,
                   "sampling_choice": sampling_choice(plan)[0],
                   # The same boundaries name an in-between stop by its own age.
                   "periods": PERIODS,
                   "sampling_options": sampling_choice(plan)[1],
                   "source_maps_public": source_maps_public() and source == "scotese2002",
                   "mask": {"id": source, "title": MASK_SOURCES[source]["title"],
                            "other": next(other for other in MASK_SOURCES if other != source),
                            "other_title": next(value["title"] for key, value
                                                in MASK_SOURCES.items() if key != source)},
                   "plates": models,
                   "motions": (atlas_motions(frames) if source == "paleoatlas2016"
                               else motions(frames, pieces_by_frame)),
                   "coastlines": coastlines(source) if enabled() else None,
                   "fields_available": any(frame["field"] for frame in frames)})


@require_safe
def source_map(request, map_id):
    if not enabled() or not source_maps_public():
        raise Http404
    item = next((item for item in catalogue("scotese2002")["maps"] if item["id"] == map_id), None)
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
    item = find_map(map_id)
    if item is None:
        raise Http404
    try:
        file = field_path(item).open("rb")
    except FileNotFoundError:
        raise Http404("Land field not generated") from None
    response = FileResponse(file, content_type="image/png")
    response["Cache-Control"] = "private, max-age=3600"
    return response


@require_safe
def coastline_file(request, age):
    """One age of the packed PaleoCoastlines, by the whole-million-year age the index lists."""
    index = coastline_index()
    if not enabled() or not index:
        raise Http404
    entry = next((entry for entry in index["ages"] if int(entry["age_ma"]) == age), None)
    if entry is None:
        raise Http404
    try:
        file = (Path(settings.PALEOCOASTLINES_DERIVED_DIR) / entry["file"]).open("rb")
    except FileNotFoundError:
        raise Http404("Coastlines not packed") from None
    response = FileResponse(file, content_type="application/json")
    response["Cache-Control"] = "public, max-age=86400"
    return response


@require_safe
def plate_file(request, model, layer):
    """Serve one packed plate-model file, by model id and layer name."""
    known = {path.stem: json.loads(path.read_text()) for path in plate_manifests()}
    if (not enabled() or layer not in PLATE_LAYERS or model not in known
            or not offerable(known[model])):
        raise Http404
    if restricted(known[model]) and not access_granted(request):
        # Locked rather than absent: the viewer offers to unlock it.
        return JsonResponse({"locked": True, "unlock": reverse("access-gate")}, status=403)
    try:
        file = plate_path(model, layer).open("rb")
    except FileNotFoundError:
        raise Http404("Plate model not packed") from None
    response = FileResponse(file, content_type="application/json")
    response["Cache-Control"] = "public, max-age=86400"
    return response
