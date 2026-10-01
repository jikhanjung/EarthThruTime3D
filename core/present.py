"""Optional, verified present-day Earth data: the satellite base, one pinned moment of wind
and clouds, and the mean surface currents (jikhanjung P10).

Built by scripts/fetch_bluemarble.py, scripts/fetch_present_weather.py and
scripts/build_ecco2_mean.py into one directory with one catalogue. Each section stands on its
own: a missing or invalid section hides only its own controls.
"""
from pathlib import Path
import re

from django.conf import settings
from django.http import Http404
from django.urls import reverse
from django.views.decorators.http import require_safe

from core.experiment_assets import DATA_ERRORS, asset_response, read_json, validate_asset

#: Section -> the asset keys it must carry and their media type
SECTIONS = {
    "base": ({"4096", "8192"}, "image/jpeg"),
    "weather": ({"10m", "250hPa", "cloud-model", "cloud-sat"}, "image/png"),
    "ocean": ({"mean"}, "image/png"),
}
_MOMENT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$")


def directory():
    return Path(settings.PRESENT_DERIVED_DIR)


def _range(pair):
    if (not isinstance(pair, list) or len(pair) != 2
            or not all(isinstance(v, (int, float)) for v in pair) or pair[0] > pair[1]):
        raise ValueError("Invalid range")
    return pair


def _section(name, data):
    keys, _ = SECTIONS[name]
    assets = data["assets"]
    if set(assets) != keys:
        raise ValueError(f"Unexpected {name} assets")
    for key, item in assets.items():
        validate_asset(item)
        if not item["file"].startswith(f"{key}-") or not (directory() / item["file"]).is_file():
            raise ValueError(f"Missing {name} asset")
    if name == "weather":
        if not _MOMENT.match(data["t"]):
            raise ValueError("Invalid moment")
        for level in ("10m", "250hPa"):
            _range(data["wind"][level]["u"])
            _range(data["wind"][level]["v"])
        if set(data["credits"]) != {"gfs", "gmgsi"}:
            raise ValueError("Missing credits")
    if name == "ocean":
        _range(data["u"])
        _range(data["v"])
        if (data["width"], data["height"]) != (1440, 720):
            raise ValueError("Unexpected ocean grid")
    return data


def catalogue():
    """{section: data} for every valid section; empty when there is nothing to show."""
    if not settings.SCOTESE_VIEWER_ENABLED:
        return {}
    try:
        document = read_json(directory() / "catalogue.json")
        if document["schema_version"] != 1:
            raise ValueError("Unknown present-day catalogue")
    except DATA_ERRORS:
        return {}
    found = {}
    for name in SECTIONS:
        try:
            if name in document:
                found[name] = _section(name, document[name])
        except DATA_ERRORS:
            continue
    return found


def _url(item):
    return reverse("present-asset", args=[item["file"]])


def globe_config():
    """What the page needs, or None when no section is available."""
    data = catalogue()
    if not data:
        return None
    config = {}
    if "base" in data:
        base = data["base"]
        config["base"] = {"urls": {k: _url(v) for k, v in base["assets"].items()},
                          "citation": base["citation"], "epoch": base["imagery_epoch"]}
    if "weather" in data:
        weather = data["weather"]
        config["weather"] = {
            "t": weather["t"],
            "wind": {level: {"url": _url(weather["assets"][level]), **weather["wind"][level]}
                     for level in ("10m", "250hPa")},
            "clouds": {kind: _url(weather["assets"][f"cloud-{kind}"]) for kind in ("sat", "model")},
            "sat_limit": weather["clouds"]["sat"]["limit_deg"],
            "credits": weather["credits"],
        }
    if "ocean" in data:
        ocean = data["ocean"]
        config["ocean"] = {"url": _url(ocean["assets"]["mean"]), "u": ocean["u"], "v": ocean["v"],
                           "period": ocean["period"], "samples": ocean["samples"],
                           "citation": ocean["citation"]}
    return config


@require_safe
def present_asset(request, filename):
    for name, data in catalogue().items():
        for item in data["assets"].values():
            if item["file"] == filename:
                return asset_response(request, directory(), item, filename, SECTIONS[name][1])
    raise Http404
