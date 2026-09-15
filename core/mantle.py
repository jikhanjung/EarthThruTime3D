"""Published OPT1 surfaces and an explicitly approximate PALEOMAP globe overlay."""
from pathlib import Path
import re

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_safe

from core.experiment_assets import (DATA_ERRORS, asset_response, catalogue as read_catalogue,
                                    logger, read_json, validate_asset)

LAYERS = ("slabs", "piles", "boundaries")


def directory():
    return Path(settings.MANTLE_DERIVED_DIR)


def catalogue():
    if not settings.SCOTESE_VIEWER_ENABLED:
        return None
    return read_catalogue(directory() / 'catalogue.json', validate_catalogue)


def validate_catalogue(data):
    if not isinstance(data['frames'], list):
        raise ValueError('Invalid mantle frames')
    for frame in data['frames']:
        if type(frame['index']) is not int or not isinstance(frame['age_ma'], (int, float)):
            raise ValueError('Invalid mantle frame')
        for name in LAYERS:
            item = frame['layers'][name]
            validate_asset(item)
            if (type(item['points']) is not int or type(item['indices']) is not int
                    or item['points'] < 0 or item['indices'] < 0
                    or item['primitive'] not in ('lines', 'triangles')
                    or item['bytes'] != item['points'] * 12 + item['indices'] * 4):
                raise ValueError('Invalid mantle geometry')


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
    return asset_response(request, directory(), item, filename, 'application/octet-stream')


def globe_overlay():
    """Only five audited source frames; partial or changed bundles fail closed."""
    try:
        return _globe_overlay()
    except DATA_ERRORS:
        logger.warning('Unavailable globe mantle overlay', exc_info=True)
        return None


def _globe_overlay():
    config = read_json(settings.BASE_DIR / "annotations/mantle-overlay.json")
    data = catalogue()
    if not data or data.get("source_archive_sha256") != config["source_archive_sha256"]:
        return None
    frames = []
    for expected in config["frames"]:
        frame = next((f for f in data["frames"] if f["age_ma"] == expected["age_ma"]), None)
        if frame is None:
            return None
        layers = {}
        for name, digest in expected["layers_sha256"].items():
            item = frame["layers"].get(name)
            if item is None or item["sha256"] != digest:
                return None
            layers[name] = {k: item[k] for k in ("points", "indices", "bytes", "primitive", "sha256")}
            layers[name]["url"] = reverse("mantle-asset", args=[item["file"]])
        frames.append({"age_ma": expected["age_ma"], "rotation_matrix": expected["rotation_matrix"],
                       "india_position_p95_deg": expected["india_position_p95_deg"], "layers": layers})
    return {"frames": frames, "cutaway": config["cutaway"],
            "strings": {"loading": _("{age} Ma 맨틀을 불러오는 중…"),
                        "ready": _("{age} Ma · 다른 복원 모델의 근사 중첩"),
                        "error": _("맨틀 자료를 불러오지 못했습니다. 다시 시도해 주세요."),
                        "residual": _("인도 경계점 위치 차이 P95: {error}°"),
                        "section": _("분홍 A–A′: OPT1 원본 단면을 근사 변환한 위치")}}
