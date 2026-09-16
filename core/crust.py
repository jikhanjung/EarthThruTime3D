"""Optional, verified present-day crust display data."""
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.urls import reverse
from django.views.decorators.http import require_safe

from core.experiment_assets import DATA_ERRORS, asset_response, read_json, validate_asset


def directory():
    return Path(settings.CRUST_DERIVED_DIR)


def catalogue():
    if not settings.SCOTESE_VIEWER_ENABLED:
        return None
    try:
        data = read_json(directory() / 'catalogue.json')
        source = read_json(settings.BASE_DIR / 'sources/crust/crust2.json')
        if (data['schema_version'] != 1 or data['source'] != source['id']
                or data['source_sha256'] != source['sha256']
                or (data['width'], data['height'], data['unit_km'], data['missing']) != (360, 180, .01, 65535)):
            raise ValueError('Invalid crust catalogue')
        item = data['asset']
        validate_asset(item)
        if item['bytes'] != 129600 or item['file'] != f"crust2-{item['sha256'][:16]}.bin":
            raise ValueError('Invalid crust grid')
        if not (directory() / item['file']).is_file():
            return None
        return data
    except DATA_ERRORS:
        return None


def globe_config():
    data = catalogue()
    if data is None:
        return None
    return {**data, 'url': reverse('crust-asset', args=[data['asset']['file']])}


@require_safe
def crust_asset(request, filename):
    data = catalogue()
    if data is None or data['asset']['file'] != filename:
        raise Http404
    return asset_response(request, directory(), data['asset'], filename, 'application/octet-stream')
