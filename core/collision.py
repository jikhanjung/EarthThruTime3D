"""An optional regional section; source geometry and illustrative physics stay separate."""
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_safe
from django.views.decorators.clickjacking import xframe_options_sameorigin

from core.experiment_assets import asset_response, catalogue as read_catalogue, validate_asset


def catalogue():
    if not settings.SCOTESE_VIEWER_ENABLED:
        return None
    return read_catalogue(Path(settings.INDIA_ASIA_DERIVED_DIR) / 'catalogue.json', validate_asset)


@require_safe
@xframe_options_sameorigin
def collision(request):
    doc = catalogue()
    return render(request, 'core/collision.html', {
        'data_url': reverse('collision-data', args=[doc['sha256'][:16]]) if doc else None,
        'strings': {
            'linkedLoading': _('메인 지구본의 같은 시점 자료를 기다리는 중…'),
            'linkedError': _('메인 지구본의 자료 로딩에 실패했습니다. 다른 시점을 선택하거나 다시 불러오세요.'),
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
    return asset_response(request, settings.INDIA_ASIA_DERIVED_DIR, doc,
                          f'section-{version}.json', 'application/json')
