"""Published OPT1 surfaces and an explicitly approximate PALEOMAP globe overlay."""
import hashlib
import json
from pathlib import Path
import re

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.cache import patch_vary_headers
from django.views.decorators.http import require_safe

LAYERS = ("slabs", "piles", "boundaries")


def directory():
    return Path(settings.MANTLE_DERIVED_DIR)


def catalogue():
    if not settings.SCOTESE_VIEWER_ENABLED:
        return None
    try:
        data = json.loads((directory() / "catalogue.json").read_text())
    except FileNotFoundError:
        return None
    if data.get("schema_version") != 1 or data.get("source") != "muller2022-opt1":
        raise ValueError("Unexpected mantle catalogue")
    return data


def accepts_gzip(header):
    qualities = {}
    for token in header.lower().split(","):
        encoding, *parameters = token.strip().split(";")
        quality = 1.0
        for parameter in parameters:
            if parameter.strip().startswith("q="):
                try:
                    quality = float(parameter.strip()[2:])
                except ValueError:
                    quality = 0
        qualities[encoding] = quality
    return 0 < qualities.get("gzip", qualities.get("*", 0)) <= 1


@require_safe
def mantle(request):
    data = catalogue()
    frames = []
    if data:
        for frame in data["frames"]:
            layers = {}
            for name in LAYERS:
                item = frame["layers"][name]
                layers[name] = {k: item[k] for k in ("points", "indices", "bytes", "primitive", "sha256")}
                layers[name]["url"] = reverse("mantle-asset", args=[item["file"]])
            frames.append({"age_ma": frame["age_ma"], "index": frame["index"], "layers": layers})
    return render(request, "core/mantle.html", {
        "frames": frames,
        "strings": {"loading": _("맨틀 구조를 불러오는 중…"),
                    "error": _("자료를 불러오지 못했습니다. 시점을 다시 선택해 주세요."),
                    "ready": _("발표된 모형 · 원본 시점"),
                    "webgl": _("이 브라우저에서 3D 화면을 시작할 수 없습니다.")},
    })


@require_safe
def mantle_asset(request, filename):
    if not re.fullmatch(r"(?:slabs|piles|boundaries)-\d{2}-[0-9a-f]{16}\.bin", filename):
        raise Http404
    data = catalogue()
    if data is None:
        raise Http404
    item = next((f["layers"][name] for f in data["frames"] for name in LAYERS
                 if f["layers"][name]["file"] == filename), None)
    if item is None:
        raise Http404
    compressed = "gzip" in item and accepts_gzip(request.headers.get("Accept-Encoding", ""))
    representation = item["gzip"] if compressed else item
    expected_name = filename + ".gz" if compressed else filename
    if representation["file"] != expected_name:
        raise Http404
    path = (directory() / expected_name).resolve()
    if not path.is_relative_to(directory().resolve()):
        raise Http404
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        raise Http404 from None
    if (len(content) != representation["bytes"]
            or hashlib.sha256(content).hexdigest() != representation["sha256"]):
        raise Http404
    response = HttpResponse(content, content_type="application/octet-stream")
    response["ETag"] = f'"{representation["sha256"]}"'
    if compressed:
        response["Content-Encoding"] = "gzip"
    patch_vary_headers(response, ["Accept-Encoding"])
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def globe_overlay():
    """Only the audited 80 Ma source pair; no implicit nearest-age substitution."""
    config = json.loads((settings.BASE_DIR / "annotations/mantle-overlay-80ma.json").read_text())
    data = catalogue()
    if not data or data.get("source_archive_sha256") != config["source_archive_sha256"]:
        return None
    frame = next((f for f in data["frames"] if f["age_ma"] == config["age_ma"]), None)
    if frame is None:
        return None
    layers = {}
    for name, digest in config["layers_sha256"].items():
        item = frame["layers"].get(name)
        if item is None or item["sha256"] != digest:
            return None
        layers[name] = {k: item[k] for k in ("points", "indices", "bytes", "primitive", "sha256")}
        layers[name]["url"] = reverse("mantle-asset", args=[item["file"]])
    return {"age_ma": config["age_ma"], "rotation_matrix": config["rotation_matrix"],
            "cutaway": config["cutaway"], "layers": layers,
            "strings": {"loading": _("80 Ma 맨틀을 불러오는 중…"),
                        "ready": _("80 Ma · 다른 복원 모델의 근사 중첩"),
                        "error": _("맨틀 자료를 불러오지 못했습니다. 다시 시도해 주세요."),
                        "unavailable": _("현재 시간 범위에서는 80 Ma 중첩을 사용할 수 없습니다.")}}
