"""Experimental published OPT1 surfaces; separate from the PALEOMAP surface model."""
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
