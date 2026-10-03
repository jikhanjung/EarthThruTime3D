"""Optional, verified present-day Earth data: the satellite base, one pinned moment of wind
and clouds, and the mean surface currents (jikhanjung P10).

Built by scripts/fetch_bluemarble.py, scripts/fetch_present_weather.py and
scripts/build_ecco2_mean.py into one directory with one catalogue. Each section stands on its
own: a missing or invalid section hides only its own controls.

The weather section may also come from PRESENT_LIVE_DIR, where the host's cron writes a new
moment once a day (jikhanjung P11). It is used while it is valid, newer than the release's own
moment and no older than LIVE_MAX_AGE; otherwise the release's moment stands. Its previous
moment's files stay servable for pages opened just before a swap.
"""
from datetime import datetime, timedelta, timezone
import json
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
#: Older than this, the daily moment yields to the release's own (two missed refreshes)
LIVE_MAX_AGE = timedelta(hours=48)


def directory():
    return Path(settings.PRESENT_DERIVED_DIR)


def live_directory():
    path = getattr(settings, "PRESENT_LIVE_DIR", None)
    return Path(path) if path else None


def moment(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)


def _range(pair):
    if (not isinstance(pair, list) or len(pair) != 2
            or not all(isinstance(v, (int, float)) for v in pair) or pair[0] > pair[1]):
        raise ValueError("Invalid range")
    return pair


def _assets(name, assets, root):
    keys, _ = SECTIONS[name]
    if set(assets) != keys:
        raise ValueError(f"Unexpected {name} assets")
    for key, item in assets.items():
        validate_asset(item)
        if not item["file"].startswith(f"{key}-") or not (root / item["file"]).is_file():
            raise ValueError(f"Missing {name} asset")


def _section(name, data, root=None):
    root = root or directory()
    _assets(name, data["assets"], root)
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
    return {**data, "root": root}


def _live_weather(release):
    """The daily moment, or None when it is missing, broken, not newer than `release`'s or
    older than LIVE_MAX_AGE."""
    root = live_directory()
    if root is None:
        return None
    try:
        document = read_json(root / "catalogue.json")
        if document["schema_version"] != 1:
            raise ValueError("Unknown live catalogue")
        data = _section("weather", document["weather"], root)
        when = moment(data["t"])
        if release and when <= moment(release["t"]):
            return None
        if datetime.now(timezone.utc) - when > LIVE_MAX_AGE:
            return None
        previous = data.get("previous", {}).get("assets")
        if previous:
            try:
                _assets("weather", previous, root)
            except DATA_ERRORS:
                data = {key: value for key, value in data.items() if key != "previous"}
        return {**data, "source": "live"}
    except DATA_ERRORS:
        return None


def catalogue():
    """{section: data} for every valid section; empty when there is nothing to show. Each
    carries `root`, the directory its files are in."""
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
    if "weather" in found:
        found["weather"] = {**found["weather"], "source": "release"}
    live = _live_weather(found.get("weather"))
    if live:
        found["weather"] = live
    return found


def status():
    """For /healthz, information only: which moment the wind and clouds show and how the
    last daily refresh went. Never a reason to call the site unhealthy."""
    weather = catalogue().get("weather")
    if not weather:
        return None
    report = {"source": weather["source"], "t": weather["t"],
              "age_h": round((datetime.now(timezone.utc) - moment(weather["t"])).total_seconds() / 3600, 1)}
    root = live_directory()
    if root is not None:
        try:
            last = json.loads((root / "status.json").read_text())
            report["refresh"] = {key: last.get(key) for key in ("at", "result", "t", "last_ok", "note")}
        except (OSError, ValueError):
            report["refresh"] = None
    return report


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
            "t": weather["t"], "source": weather["source"],
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
        listed = list(data["assets"].values()) + list(data.get("previous", {}).get("assets", {}).values())
        for item in listed:
            if item["file"] == filename:
                return asset_response(request, data["root"], item, filename, SECTIONS[name][1])
    raise Http404
