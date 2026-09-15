"""An optional regional section; source geometry and illustrative physics stay separate."""
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.cache import patch_vary_headers
from django.utils.translation import gettext as _
from django.views.decorators.http import require_safe
from django.views.decorators.clickjacking import xframe_options_sameorigin

from core.mantle import accepts_gzip


def catalogue():
    if not settings.SCOTESE_VIEWER_ENABLED:
        return None
    try:
        doc = json.loads((Path(settings.INDIA_ASIA_DERIVED_DIR)/'catalogue.json').read_text())
    except FileNotFoundError:
        return None
    if doc.get('schema_version') != 1 or doc.get('source') != 'muller2022-opt1':
        raise ValueError('Unexpected section catalogue')
    return doc


@require_safe
@xframe_options_sameorigin
def collision(request):
    doc = catalogue()
    return render(request, 'core/collision.html', {
        'data_url': reverse('collision-data', args=[doc['sha256'][:16]]) if doc else None,
        'strings': {
            'loading': _('단면 자료를 불러오는 중…'), 'error': _('단면을 불러오지 못했습니다.'),
            'cratons': _('대륙 핵부 윤곽'), 'boundaries': _('판 경계'),
            'section': _('맨틀 구조의 실제 교차선'), 'flow': _('대류 개념도 · 속도 자료 없음'),
            'crust': _('국소 지각 변형 · 가정 모형'), 'thickness': _('지각 두께'),
            'shortening': _('누적 단축'), 'uplift': _('등압평형 융기'),
            'south': _('남쪽'), 'north': _('북쪽'), 'depth': _('깊이'),
            'distance': _('국소 거리'), 'play': _('재생'), 'pause': _('정지'),
            'original': _('원본 시점'), 'exaggeration': _('수직 배율'),
            'surfaceError': _('3D 지표를 시작할 수 없습니다. 단면은 계속 볼 수 있습니다.'),
        },
    })


@require_safe
def collision_data(request, version):
    doc = catalogue()
    if doc is None or version != doc['sha256'][:16]:
        raise Http404
    use_gzip = accepts_gzip(request.headers.get('Accept-Encoding', ''))
    asset = doc['gzip'] if use_gzip else doc
    filename = f'section-{version}.json' + ('.gz' if use_gzip else '')
    if asset['file'] != filename:
        raise Http404
    base = Path(settings.INDIA_ASIA_DERIVED_DIR).resolve()
    path = (base/filename).resolve()
    if not path.is_relative_to(base):
        raise Http404
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        raise Http404 from None
    if len(content) != asset['bytes'] or hashlib.sha256(content).hexdigest() != asset['sha256']:
        raise Http404
    response = HttpResponse(content, content_type='application/json')
    if use_gzip:
        response['Content-Encoding'] = 'gzip'
    response['ETag'] = f'"{asset["sha256"]}"'
    response['Cache-Control'] = 'public, max-age=31536000, immutable'
    patch_vary_headers(response, ['Accept-Encoding'])
    return response
