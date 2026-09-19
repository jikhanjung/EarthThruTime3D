"""Local reference globe catalogue; all asset paths come from the pinned manifest."""
import json
import logging
import math
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
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
                       "title": gettext_lazy("PALEOMAP PaleoAtlas (2016)")},
    "scotese2002": {"catalogue": "sources/scotese-earth-history.json",
                    "directory": "SCOTESE_DERIVED_DIR",
                    "title": gettext_lazy("Scotese PALEOMAP 웹 지도 (2002)")},
    # Elevation grids rather than pictures: the 109 PaleoDEMs (Scotese & Wright 2018),
    # 0-540 Ma at 5 Myr, CC BY 4.0, as textures holding coastline distance and height.
    # The timeline is fronted by the 2016 atlas maps older than the grids, as masks.
    "paleodem2018": {"catalogue": "sources/paleodem-slices.json",
                     "directory": "PALEODEM_DERIVED_DIR",
                     "title": gettext_lazy("PALEOMAP PaleoDEM 고도 격자 (2018)")},
}
DEFAULT_MASK_SOURCE = "paleoatlas2016"
# The toolbar's dataset picker, in its order: the default, the elevation series, then the
# 2002 maps kept for comparison.
DATASET_LABELS = {"paleoatlas2016": gettext_lazy("PaleoAtlas 2016"),
                  "paleodem2018": gettext_lazy("고도 격자"),
                  "scotese2002": gettext_lazy("웹 지도 2002")}
# Below the oldest grid the elevation timeline continues with these atlas maps.
DEM_OLDEST_MA = 540.0

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
    """Label for a 2016 atlas map, from its age alone, in the active language."""
    if item["id"].endswith("-lgm"):
        return _("최후빙기 최성기")
    if item["age_ma"] == 0:
        return _("현재")
    for upper, label in PERIODS:
        if item["age_ma"] < upper:
            return _(label)
    return _("원생대")


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
    """Which mask source a catalogue entry belongs to.

    2002 entries carry an image, PaleoDEM entries a grid file, atlas entries neither.
    """
    if "image" in item:
        return "scotese2002"
    return "paleodem2018" if "file" in item else "paleoatlas2016"


def derived_path(item, suffix):
    source = source_of(item)
    stem = Path(item["image"]["path"]).stem if source == "scotese2002" else item["id"]
    directory = getattr(settings, MASK_SOURCES[source]["directory"])
    return Path(directory) / f"{stem}-{suffix}"


def field_path(item):
    """Equirectangular signed-distance field: the form the viewer interpolates."""
    return derived_path(item, "field.png")


def ice_path(item):
    """Present-day ice mask rasterised by scripts/build_ice.py; only the 0 Ma grid has one."""
    return derived_path(item, "ice.png")


def ice_sources():
    """Where each grid's ice mask came from, as scripts/build_ice.py wrote it beside the masks:
    natural-earth, atlas, or limit for a cap at a modelled ice latitude. Empty until built."""
    path = Path(settings.PALEODEM_DERIVED_DIR) / "ice-sources.json"
    if not path.exists():
        return {"grids": {}, "sheets": {}, "lows": {}, "model_levels": []}
    document = json.loads(path.read_text())
    return {**{key: document.get(key, {}) for key in ("grids", "sheets", "lows")},
            # PaleoMIST's own sea level per step, [age_ka, level_m] oldest first, for the
            # window's strip to draw beside the stack's; empty before the model slices.
            "model_levels": document.get("model_levels", [])}


def lows_of(kinds, item):
    """The sidecar's lowstand slices for a grid; a sidecar from before the slices held one
    drawn lowstand as a dict, which is stale and counts as none."""
    lows = kinds["lows"].get(item["id"], [])
    return lows if isinstance(lows, list) else []


def what_if_lows(kinds, item):
    """The slices the sea-level what-if mixes between: those that lower the sea below every
    younger slice. A sidecar from before `lowers` wrote only those, so a missing flag counts."""
    return [low for low in lows_of(kinds, item) if low.get("lowers", True)]


# The time window: instead of the whole series, the last deglaciation one thousand years at
# a stop, where the present's dated slices give every age its own ice and sea level.
WINDOWS = {"deglacial": 25, "lastcycle": 130}   # how far back each reaches, in thousands of years
WINDOW_OPTIONS = [("", gettext_lazy("전체 시대")), ("deglacial", gettext_lazy("최근 2.5만 년")),
                  ("lastcycle", gettext_lazy("최근 13만 년"))]
HOLOCENE_KA = 11.7
DEGLACIAL_SOURCE = "https://doi.org/10.5281/zenodo.8161764"
STACK_SOURCE = "https://doi.org/10.5194/cp-12-1079-2016"
PALEOMIST_SOURCE = "https://doi.org/10.1594/PANGAEA.905800"


def time_window(request, source):
    """The window asked for, where the series can have one; anything else is the whole series."""
    asked = request.GET.get("window") if request is not None else None
    return asked if asked in WINDOWS and source == "paleodem2018" else None


def window_frames(frames, kinds, stack, reach):
    """A window's frames: the present grid once per thousand years from `reach` ka, oldest
    first, then the present itself; None where the deglacial slices have not been built.

    Every frame is the 0 Ma grid, so the terrain is today's, and every one carries its age
    as `deglacial` {age_ka, level_m, url}. Where NADI-1 and DATED-1 give that age a slice
    the ice is the slice (`dated`), at the slice's level, the stack's running minimum; the
    sheet and the what-if slices are dropped, as the age sets the sea level. Where the slice
    is PaleoMIST's modelled ice instead (`reconstructed`, 26 to 80 ka where built) the same
    path shows it, at the stack's own level for the age, which PaleoMIST's own level
    disagrees with; the page says so. Older than any slice there is no reconstruction to
    show, so the frame keeps them and the page mixes the slices at the stack's own level for
    that age (`analogue`): the retreat's shape at the same sea level, an assumption the page
    names. No window frame has a temperature: the present's 5 Myr map would read as the
    climate of a glacial maximum, which it says nothing about. What a frame can have is
    `climate`, its own thousand years of Krapp et al. 2021: modelled plant cover and annual
    precipitation, where scripts/build_climate.py has built it.
    """
    present = next((frame for frame in frames if frame["relief"] and frame["age"] == 0 and frame["ice"]), None)
    if present is None:
        return None
    item = find_map(present["id"])
    slices = {low["age_ka"]: low for low in lows_of(kinds, item) if ice_low_path(item, low["age_ka"]).exists()}
    if not slices:
        return None
    levels = {int(round(age)): level for age, level in stack}
    # The window's stops pick their rivers by age, so every step goes, not only the ones
    # that lower the sea; the page brackets the age between two and mixes them.
    steps = rivers_ice_steps(item) if present.get("rivers") else None
    present = dict(present, rivers_ice=([{key: step[key] for key in ("age_ka", "level_m", "url")}
                                         for step in steps] if steps else None))
    window = []
    for age in range(reach, 0, -1):
        low = slices.get(age)
        if low is None and age not in levels:
            continue
        shared = dict(age=age / 1000, temp=None, mean_c=None, climate=climate_url(item, age),
                      label=_("홀로세") if age < HOLOCENE_KA else _("플라이스토세"))
        if low is not None:
            modelled = low.get("source") == "paleomist"
            window.append(dict(present, **shared, ice_kind="reconstructed" if modelled else "dated",
                               ice_sheet=None, ice_lows=None,
                               title=f"PaleoMIST 1.0, {age} ka" if modelled else f"NADI-1 · DATED-1, {age} ka",
                               source=PALEOMIST_SOURCE if modelled else DEGLACIAL_SOURCE,
                               deglacial={"age_ka": age, "level_m": low["level_m"],
                                          "url": reverse("globe-ice-low", args=[present["id"], age])}))
        else:
            window.append(dict(present, **shared, ice_kind="analogue",
                               title=str(_("가정 빙하: 해수면이 같았던 후퇴기의 모양")), source=STACK_SOURCE,
                               deglacial={"age_ka": age, "level_m": levels[age], "url": None}))
    window.append(dict(present, temp=None, mean_c=None, ice_sheet=None, ice_lows=None,
                       climate=climate_url(item, 0),
                       deglacial={"age_ka": 0, "level_m": 0.0, "url": None}))
    return window


def ice_low_path(item, age):
    """One dated lowstand field for the ice, a slice of the present's deglaciation at `age`
    thousand years; only where built."""
    return derived_path(item, f"ice-low-{age}.png")


def climate_path(item, age):
    """Modelled plant cover and annual precipitation at `age` thousand years, from Krapp et
    al. 2021 by scripts/build_climate.py; only where built."""
    return derived_path(item, f"climate-{age}.png")


def climate_url(item, age):
    return reverse("globe-climate", args=[item["id"], age]) if climate_path(item, age).exists() else None


def temperature_path(item):
    """Surface air temperature texture from the Scotese 2021 maps, built for the grids."""
    return derived_path(item, "temp.png")


def river_url(view, args):
    # RGB river/lake fields are incompatible with cached grayscale fields from v0.14.
    return reverse(view, args=args) + "?format=river-lake-rgb-v1"


def rivers_path(item):
    """Potential drainage routed over the grid by scripts/build_rivers.py, one field per grid."""
    return derived_path(item, "rivers.png")


def rivers_low_path(item):
    """The same drainage routed with the sea at the grid's lowest slider level; only where the
    slider reaches below the datum."""
    return derived_path(item, "rivers-low.png")


def rivers_low_of(kinds, item):
    """The lowstand river field and its level, or None: the level is the bottom of the ice
    sidecar's slider range, the same figure the page holds the slider to."""
    sheet = kinds["sheets"].get(item["id"])
    level = sheet["range_m"][0] if sheet and sheet.get("range_m") else 0
    if level >= 0 or not rivers_low_path(item).exists():
        return None
    return {"url": river_url("globe-rivers-low", [item["id"]]), "level_m": level}


def rivers_ice_path(item, years):
    """The grid's rivers routed over the ice of one PaleoMIST step, named by its age in years."""
    return derived_path(item, f"rivers-ice-{years}.png")


def rivers_ice_steps(item):
    """Every river field routed over the ice, youngest first, each with the sea level it was
    routed at and whether that level is below every younger step's, from the sidecar
    scripts/build_rivers.py --ice writes; only where the file exists. None where there are
    none, or the sidecar is not in order."""
    path = derived_path(item, "rivers-ice.json")
    if not path.exists():
        return None
    try:
        steps, previous_age = [], 0
        for step in json.loads(path.read_text())["slices"]:
            age, level = step["age_ka"], step["level_m"]
            if (not isinstance(age, (int, float)) or not isinstance(level, (int, float))
                    or not math.isfinite(age) or not math.isfinite(level) or not previous_age < age <= 80):
                raise ValueError("Ice river slices must increase in age")
            previous_age = age
            years = int(round(age * 1000))
            if rivers_ice_path(item, years).exists():
                steps.append({"age_ka": age, "level_m": level, "lowers": bool(step.get("lowers")),
                              "url": river_url("globe-rivers-ice", [item["id"], years])})
        return steps or None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        logging.getLogger(__name__).warning("Unavailable ice river sidecar: %s", path, exc_info=True)
        return None


def rivers_ice_of(item):
    """The steps the sea-level what-if can bracket by level: only those whose level is below
    every younger step's, so the levels fall with age. None where there are none."""
    steps = rivers_ice_steps(item)
    if not steps:
        return None
    slices, previous_level = [], 0
    for step in steps:
        if not step["lowers"]:
            continue
        if not step["level_m"] < previous_level:
            logging.getLogger(__name__).warning("Ice river slice at %s ka is marked as lowering but does not", step["age_ka"])
            return None
        previous_level = step["level_m"]
        slices.append({key: step[key] for key in ("age_ka", "level_m", "url")})
    return slices or None


def sealevel_curve():
    """The long-term and Pleistocene sea-level curves and each grid's datum, as
    scripts/build_sealevel.py wrote them. Absent until that script has run."""
    path = Path(settings.PALEODEM_DERIVED_DIR) / "sealevel-curve.json"
    if not path.exists():
        return {"long": [], "pleistocene": [], "stops": {}}
    return json.loads(path.read_text())


def temperature_curve():
    """Global mean temperature per map and per stop, as scripts/build_paleotemp.py wrote it.

    Absent until that script has run. The curve is an area-weighted mean of published
    1 degree maps, so it is a derived number, not a proxy measurement.
    """
    path = Path(settings.PALEODEM_DERIVED_DIR) / "paleotemp-curve.json"
    if not path.exists():
        return {"curve": [], "stops": {}}
    return json.loads(path.read_text())


@lru_cache(maxsize=4)
def catalogue(source="scotese2002"):
    return json.loads((settings.BASE_DIR / MASK_SOURCES[source]["catalogue"]).read_text())


def series_items(source):
    """The catalogue entries a source shows, oldest first.

    The elevation series has no grid older than 540 Ma, and a frame without a field has
    nothing to fall back to there, so it is fronted by the 2016 atlas maps beyond that
    age, drawn as masks; the other sources show their own catalogue.
    """
    items = catalogue(source)["maps"]
    if source != "paleodem2018":
        return items
    prelude = [item for item in catalogue("paleoatlas2016")["maps"] if item["age_ma"] > DEM_OLDEST_MA]
    return prelude + items


def complete(source):
    """Whether every field a source shows exists."""
    return all(field_path(item).exists() for item in series_items(source))


def mask_source(request=None):
    """The mask source to show: a per-request comparison override, then the setting.

    A visitor's override to the elevation series is honoured only when the whole series
    is built: a frame without a field has no map to fall back to there. The setting is
    trusted as it is, like the other sources, and /healthz reports what it is missing.
    """
    asked = request.GET.get("masks") if request is not None else None
    if asked in MASK_SOURCES and (asked != "paleodem2018" or complete(asked)):
        return asked
    configured = getattr(settings, "MASK_SOURCE", DEFAULT_MASK_SOURCE)
    return configured if configured in MASK_SOURCES else DEFAULT_MASK_SOURCE


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


# A grid borrows the segmentation of the atlas map nearest its age; beyond this distance
# there is nothing of the same paleogeography to borrow.
NEAREST_ATLAS_MA = 5.0


def nearest_atlas_map(age):
    """The 2016 atlas map nearest an age, within NEAREST_ATLAS_MA; None beyond that."""
    maps = catalogue("paleoatlas2016")["maps"]
    item = min(maps, key=lambda entry: (abs(entry["age_ma"] - age), entry["age_ma"]))
    return item if abs(item["age_ma"] - age) <= NEAREST_ATLAS_MA else None


def piece_report(item):
    """The segmentation report's pieces for one map, or an empty list.

    A PaleoDEM grid is never segmented. It is the same paleogeography as the 2016 atlas,
    from the same edition, so it borrows the pieces of the atlas map nearest its age: 81
    of the 109 grids share an age with a map, the rest are within 5 Myr of one. The names
    then sit where the atlas drew them, a few degrees off at most on the borrowed ages.
    """
    if source_of(item) == "paleodem2018":
        item = nearest_atlas_map(item["age_ma"])
        if item is None:
            return []
    path = derived_path(item, "pieces.json")
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("pieces", [])


def landmass_names(pieces):
    """Named points for the globe, in the active language where an English name exists."""
    english = translation.get_language() == "en"
    return [{"name": (name.get("name_en") or name["name"]) if english else name["name"],
             "lon": name["lon"], "lat": name["lat"]}
            for piece in pieces for name in piece.get("names", [])
            if name.get("display", True)]


# Text the viewer script shows. Translated here, where the request's language is known,
# and handed to the page as JSON. {placeholders} are filled in by the script.
def viewer_strings():
    return {
        "present": _("현재"),
        "yearsAgo": _("{years}년 전"),
        "playStart": _("▶ 시대 순서 재생"),
        "playStop": _("❚❚ 재생 멈춤"),
        "mapless": _("지도 없는 시대"),
        "maplessValue": _("{age}, 지도 없음, 판 재구성만"),
        "betweenValue": _("{period} 사이, {age}, 보간"),
        "olderThanMaps": _("가장 오래된 지도보다 이전"),
        "mask": _("대륙 마스크"),
        "relief": _("고도"),
        "reliefGlobe": _("고도 지구본"),
        "loadingRelief": _("{period} 고도 지구본을 불러오는 중…"),
        "temperature": _("기온"),
        "temperatureGlobe": _("기온 지구본"),
        "loadingTemperature": _("{period} 기온 지도를 불러오는 중…"),
        "vegetation": _("모형 식생"),
        "vegetationGlobe": _("모형 식생 지구본"),
        "rainfall": _("모형 강수"),
        "rainfallGlobe": _("모형 강수 지구본"),
        "loadingClimate": _("{period} 기후 모형 지도를 불러오는 중…"),
        "meanTemperature": _("전 지구 평균 기온 약 {value} °C{between}"),
        "meanTemperatureBetween": _(" (보간)"),
        "meanTemperatureNone": _("전 지구 평균 기온: 자료 없음 (540 Ma 이전)"),
        "meanTemperatureDelta": _(" · 현재보다 {delta} °C"),
        "seaLevel": _("장기 해수면 약 {value} (현재 대비){offset}"),
        "seaLevelOffset": _(" · 표시 보정 {value}"),
        "seaLevelIce": _(" · 빙하 {value}백만 km³"),
        "seaMarkNone": _("빙하 없음 {value}"),
        "seaMarkMax": _("빙하 최대 {value}"),
        "seaNoIce": _("이 시점에는 얼음이 없어 해수면을 옮길 수 없습니다"),
        "seaLevelNone": _("장기 해수면: 자료 없음 (540 Ma 이전)"),
        "seaLevelDated": _("해수면 약 {value} (현재 대비, 그 나이의 Spratt & Lisiecki 2016 값)"),
        "seaFromAge": _("이 범위에서는 해수면이 나이에서 정해져 옮길 수 없습니다"),
        "noMap": _("지도 없음"),
        "interpolated": _("보간"),
        "sourceAlt": _("{label} ({age}) Scotese 원본 지도"),
        "maplessCount": _("{age} Ma · 지도 없음"),
        "betweenCount": _("{age} · 보간"),
        "loadingPlates": _("{age} 판 재구성을 불러오는 중…"),
        "loadingMask": _("{period} 대륙 마스크를 불러오는 중…"),
        "loadingMap": _("{period} 지도를 불러오는 중…"),
        "maplessLabel": _("{age}. 이 시대의 지도는 없고 판 재구성만 표시합니다."),
        "globeLabel": _("{period}, {age} {surface}{between}. 드래그 또는 방향키로 회전, 더하기 빼기로 확대 축소."),
        "maskGlobe": _("대륙 마스크 지구본"),
        "globe": _("지구본"),
        "betweenSuffix": _(", 보간된 중간 형태"),
        "shownPlates": _("{age} 판 재구성 표시 완료"),
        "shownSurface": _("{period} {surface} 표시 완료{between}"),
        "shownBetween": _(" (보간)"),
        "failedField": _("대륙 거리장을 불러오지 못했습니다. 분할 결과 파일을 확인해 주세요."),
        "failedMap": _("지도를 불러오지 못했습니다. 로컬 원본 파일과 연결을 확인해 주세요."),
        "gestureGlobe": _("드래그로 회전 · 오른쪽 드래그로 이동 · 휠 클릭 / Shift 드래그로 기울이기 · 스크롤 / 핀치로 확대"),
        "gestureTerrain": _("드래그로 회전 · 휠 클릭 드래그로 기울이기 · 스크롤 / 핀치로 확대"),
        "gestureSheet": _("드래그로 회전 · 오른쪽 드래그로 이동 · 스크롤 / 핀치로 확대"),
        "modelReach": _("{title} 모델은 {reach} Ma까지입니다. "),
        "modelsDeeper": _("{models}를 고르면 이 시대가 나옵니다."),
        "noModelDeeper": _("이 시대에 닿는 모델이 아직 없습니다."),
        "modelFrame": _("{title} · 기준틀 {frame} · {reach} Ma까지"),
        "noCoastline": _("{age}에서 {reach} Myr 안에 해안선 자료가 없습니다. 자료는 0~{oldest} Ma입니다."),
        "coastlineAt": _("{age} Ma 해안선"),
        "coastlineNearest": _("가장 가까운 {age} Ma 해안선을 그렸습니다 (지금 {now})."),
        "coastlineCarried": _("{age} Ma 해안선을 판 운동을 따라 {now}까지 옮겨 그렸습니다."),
        "contextLost": _("그래픽 연결이 끊겼습니다. 페이지를 새로고침해 주세요."),
        "oldestNoMap": _("{age} Ma · 지도 없음"),
        "oldestPast": _("{age} Ma · 과거"),
        "oldestWindow": _("{age} ka · 과거"),
        "analogueIce": _("가정 빙하"),
        "reconstructedIce": _("모델 복원 빙상"),
        "webglFailed": _("3D 화면을 시작하지 못했습니다. WebGL을 지원하는 브라우저에서 하드웨어 가속을 확인해 주세요."),
        "proterozoic": _("원생대"),
    }


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


def atlas_motions(frames, source="paleoatlas2016"):
    """Per gap, the landmasses carried by the PALEOMAP rotations, oldest gap first.

    scripts/atlas_motions.py writes these for the 2016 atlas and scripts/paleodem_motions.py
    for the elevation series, each from the rotation model, so nothing is matched here.
    The file, in the source's own directory, has to describe exactly these frames in this
    order; anything else is ignored rather than applied to the wrong gap, and the maps
    then blend in place.
    """
    path = Path(getattr(settings, MASK_SOURCES[source]["directory"])) / "motions.json"
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

    Offered over the 2016 masks and the elevation grids: all three are PALEOMAP, so the
    lines sit on them with no rotation (devlog 026). Over the 2002 maps, whose longitudes
    drift from that frame, the same lines would look like a disagreement they are not.
    """
    index = coastline_index()
    if source == "scotese2002" or not index:
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


SAMPLING_OPTIONS = [("steps:4", gettext_lazy("지도마다 4단계")), ("interval:1", "1 Myr"),
                    ("interval:5", "5 Myr"), ("interval:10", "10 Myr")]


def sampling_choice(plan):
    """The timeline control's value for a plan, and the options it offers."""
    if plan["interval_ma"]:
        choice, label = f"interval:{plan['interval_ma']:g}", f"{plan['interval_ma']:g} Myr"
    else:
        choice, label = f"steps:{plan['steps']}", _("지도마다 {steps}단계").format(steps=plan["steps"])
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
            # A menu title may carry a Korean note such as "(비공개)"; the catalogue is
            # the source string and locale/ holds its English.
            "short": _(document.get("menu_title", document["short_title"])),
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
    maps = series_items(source)
    missing = [item["id"] for item in maps if not field_path(item).exists()]
    return {"required": True, "source": source, "expected": len(maps),
            "missing": len(missing), "missing_ids": missing[:5]}


@require_safe
def globe(request):
    frames = []
    pieces_by_frame = {}
    source = mask_source(request)
    climate = {"curve": [], "stops": {}}
    sea = {"long": [], "pleistocene": [], "stops": {}}
    kinds = {"grids": {}, "sheets": {}, "lows": {}, "model_levels": []}
    if enabled():
        document = catalogue(source)
        if source == "paleodem2018":
            climate = temperature_curve()
            sea = sealevel_curve()
            kinds = ice_sources()
        if source == "scotese2002":
            entries = [(item, _(korean), item["image_label"],
                        BOUNDS[item["id"].removeprefix("scotese-")],
                        reverse("globe-map", args=[item["id"]]) if source_maps_public() else None,
                        item["page"]["url"])
                       for item, korean in zip(document["maps"], KOREAN_LABELS)]
        else:
            # The 2016 rasters are never served, published or not: their licence is not
            # yet confirmed, so only the fields derived from them reach the page. The
            # elevation series is grids, served as textures; its atlas prelude is masks.
            entries = [(item, period_label(item), item["label"], None, None,
                        catalogue(source_of(item))["license"]["source"])
                       for item in series_items(source)]
        for item, korean, title, bounds, url, link in entries:
            pieces_by_frame[item["id"]] = piece_report(item)
            given = climate["stops"].get(item["id"])
            iced = source == "paleodem2018" and ice_path(item).exists()
            frames.append({"id": item["id"], "label": korean, "title": title,
                           "age": item["age_ma"], "bounds": bounds, "url": url,
                           "relief": source_of(item) == "paleodem2018",
                           "temp": (reverse("globe-temperature", args=[item["id"]])
                                    if given and temperature_path(item).exists() else None),
                           "mean_c": given["mean_c"] if given else None,
                           "sea_m": sea["stops"].get(item["id"]),
                           "ice": reverse("globe-ice", args=[item["id"]]) if iced else None,
                           # natural-earth, atlas, or limit: a cap at a modelled ice latitude,
                           # which the page flags as a limit rather than an outline.
                           "ice_kind": kinds["grids"].get(item["id"]) if iced else None,
                           # The paper's ice volume and the area inside each level of the
                           # mask's distance field, so the page can cut it where the sea-level
                           # offset's volume says; and the dated lowstand slices where a
                           # deglaciation is reconstructed, each with its sea level, youngest first.
                           "ice_sheet": kinds["sheets"].get(item["id"]) if iced else None,
                           "ice_lows": ([dict(low, url=reverse("globe-ice-low", args=[item["id"], low["age_ka"]]))
                                         for low in what_if_lows(kinds, item)
                                         if ice_low_path(item, low["age_ka"]).exists()] if iced else None),
                           # Potential drainage routed over the grid itself; only where built.
                           "rivers": (river_url("globe-rivers", [item["id"]])
                                      if source == "paleodem2018" and rivers_path(item).exists() else None),
                           # The shelf's rivers at the slider's lowest level, mixed in as the sea drops.
                           "rivers_low": (rivers_low_of(kinds, item)
                                          if source == "paleodem2018" and rivers_path(item).exists() else None),
                           # The rivers routed over the ice of the last glacial cycle, one field per
                           # PaleoMIST step with its sea level; the page brackets its level between
                           # two, in the what-if and in the time windows alike.
                           "rivers_ice": (rivers_ice_of(item)
                                          if source == "paleodem2018" and rivers_path(item).exists() else None),
                           "field": (reverse("globe-field", args=[item["id"]])
                                     if field_path(item).exists() else None),
                           "names": landmass_names(pieces_by_frame[item["id"]]),
                           "source": link})
    plan = sampling(request)
    models = plate_models(request)
    deepest = max((model["covers"][1] for model in models), default=None)
    window = time_window(request, source)
    windowed = (window_frames(frames, kinds, sea["pleistocene"], WINDOWS[window or "deglacial"])
                if source == "paleodem2018" else None)
    if windowed is None:
        window = None
    if window:
        # One stop per thousand years and nothing older: the deep, map-less stops belong
        # to the whole series, not to a glacial cycle of it.
        frames, plan, deepest = windowed, {"interval_ma": None, "steps": 1}, None
    plan["window"] = window
    from core.mantle import globe_overlay
    from core.crust import globe_config as crust_config
    stops = timeline(frames, plan, deepest)
    overlay = (globe_overlay() if source in ("paleoatlas2016", "paleodem2018")
               and not window and all(any(abs(stop[3] - age) < 1e-8 for stop in stops) for age in (80, 60, 40, 20, 0)) else None)
    return render(request, "core/home.html",
                  {"frames": frames, "viewer_enabled": enabled(), "mantle_overlay": overlay,
                   "crust": crust_config(),
                   "crust_strings": {
                       "caption": _("CRUST 2.0 · 현재 지각 · 구면 기준 두께 ×{scale}"),
                       "ready": _("CRUST 2.0 · 현재 지구 · 원모델 2° · 위치를 클릭하면 두께를 표시합니다."),
                       "loading": _("지각 두께를 불러오는 중…"),
                       "unavailable": _("현재 지구 자료 — 이 연대에는 제공되지 않음"),
                       "error": _("지각 자료를 불러오지 못했습니다. 다시 시도해 주세요."),
                       "missing": _("이 위치에는 지각 두께 값이 없습니다."),
                       "value": _("경도 {lon}° · 위도 {lat}° · 약 {km} km (표시용 격자)"),
                   },
                   "stops": stops, "sampling": plan,
                   "window": window, "window_options": WINDOW_OPTIONS if windowed else None,
                   "sampling_choice": sampling_choice(plan)[0],
                   # The same boundaries name an in-between stop by its own age.
                   "periods": [(upper, _(name)) for upper, name in PERIODS],
                   "strings": viewer_strings(),
                   "sampling_options": sampling_choice(plan)[1],
                   "source_maps_public": source_maps_public() and source == "scotese2002",
                   "mask": {"id": source, "title": str(MASK_SOURCES[source]["title"]),
                            "relief": source == "paleodem2018",
                            # The panel's dataset picker: the default, the elevation series
                            # once it is whole, then the 2002 maps kept for comparison.
                            # It sits in the toolbar, so each choice has a short label and
                            # keeps the full title for the tooltip.
                            "choices": [(key, str(DATASET_LABELS[key]), str(MASK_SOURCES[key]["title"]))
                                        for key in DATASET_LABELS
                                        if key == source or key != "paleodem2018" or complete(key)],
                            # A comparison link only to a series that can be shown.
                            "others": [(key, str(value["title"])) for key, value
                                       in MASK_SOURCES.items()
                                       if key != source and (key != "paleodem2018" or complete(key))]},
                   "plates": models,
                   "motions": (motions(frames, pieces_by_frame) if source == "scotese2002"
                               else atlas_motions(frames, source)),
                   "coastlines": coastlines(source) if enabled() else None,
                   "temperature_curve": climate["curve"],
                   "temperature_available": any(frame.get("temp") for frame in frames),
                   "climate_available": any(frame.get("climate") for frame in frames),
                   "sealevel": {"long": sea["long"], "pleistocene": sea["pleistocene"],
                                "model": kinds["model_levels"] if window else []},
                   "sealevel_available": bool(sea["long"]),
                   "ice_available": any(frame.get("ice") for frame in frames),
                   "rivers_available": any(frame.get("rivers") for frame in frames),
                   "rivers_ice_available": any(frame.get("rivers_ice") for frame in frames),
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
def ice_mask(request, map_id):
    if not enabled():
        raise Http404
    item = find_map(map_id)
    if item is None:
        raise Http404
    try:
        file = ice_path(item).open("rb")
    except FileNotFoundError:
        raise Http404("Ice mask not generated") from None
    response = FileResponse(file, content_type="image/png")
    response["Cache-Control"] = "private, max-age=3600"
    return response


@require_safe
def river_field(request, map_id):
    if not enabled():
        raise Http404
    item = find_map(map_id)
    if item is None:
        raise Http404
    try:
        file = rivers_path(item).open("rb")
    except FileNotFoundError:
        raise Http404("River field not generated") from None
    response = FileResponse(file, content_type="image/png")
    response["Cache-Control"] = "private, max-age=3600"
    return response


@require_safe
def river_low_field(request, map_id):
    if not enabled():
        raise Http404
    item = find_map(map_id)
    if item is None:
        raise Http404
    try:
        file = rivers_low_path(item).open("rb")
    except FileNotFoundError:
        raise Http404("Lowstand river field not generated") from None
    response = FileResponse(file, content_type="image/png")
    response["Cache-Control"] = "private, max-age=3600"
    return response


@require_safe
def river_ice_field(request, map_id, years):
    if not enabled():
        raise Http404
    item = find_map(map_id)
    if item is None:
        raise Http404
    try:
        file = rivers_ice_path(item, years).open("rb")
    except FileNotFoundError:
        raise Http404("Ice river field not generated") from None
    response = FileResponse(file, content_type="image/png")
    response["Cache-Control"] = "private, max-age=3600"
    return response


@require_safe
def ice_low(request, map_id, age):
    if not enabled():
        raise Http404
    item = find_map(map_id)
    if item is None:
        raise Http404
    try:
        file = ice_low_path(item, age).open("rb")
    except FileNotFoundError:
        raise Http404("Ice lowstand not generated") from None
    response = FileResponse(file, content_type="image/png")
    response["Cache-Control"] = "private, max-age=3600"
    return response


@require_safe
def climate_map(request, map_id, age):
    item = find_map(map_id) if enabled() else None
    if item is None:
        raise Http404
    try:
        file = climate_path(item, age).open("rb")
    except FileNotFoundError:
        raise Http404("Climate texture not generated") from None
    response = FileResponse(file, content_type="image/png")
    response["Cache-Control"] = "private, max-age=3600"
    return response


@require_safe
def temperature_map(request, map_id):
    if not enabled():
        raise Http404
    item = find_map(map_id)
    if item is None:
        raise Http404
    try:
        file = temperature_path(item).open("rb")
    except FileNotFoundError:
        raise Http404("Temperature texture not generated") from None
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
