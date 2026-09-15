"""Verified optional experiment data, cached by filesystem identity, never by URL alone."""
from collections import OrderedDict
from functools import lru_cache
import hashlib
import json
import logging
import os
from pathlib import Path
from threading import Lock

from django.http import FileResponse, Http404, HttpResponseNotModified
from django.utils.cache import patch_vary_headers
from django.utils.http import parse_etags

logger = logging.getLogger(__name__)
DATA_ERRORS = (OSError, ValueError, KeyError, TypeError, AttributeError)


def signature(stat):
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


@lru_cache(maxsize=16)
def _json(path, identity):
    with path.open('rb') as handle:
        if signature(os.fstat(handle.fileno())) != identity:
            raise ValueError('Catalogue changed while opening')
        data = json.load(handle)
        if signature(os.fstat(handle.fileno())) != identity:
            raise ValueError('Catalogue changed while reading')
    return data


def read_json(path):
    path = Path(path).resolve()
    return _json(path, signature(path.stat()))


def catalogue(path, validate):
    try:
        data = read_json(path)
        if data['schema_version'] != 1 or data['source'] != 'muller2022-opt1':
            raise ValueError('Unexpected experiment catalogue')
        validate(data)
        return data
    except FileNotFoundError:
        return None
    except DATA_ERRORS:
        logger.warning('Unavailable experiment catalogue: %s', path, exc_info=True)
        return None


def validate_asset(item):
    if (not isinstance(item['file'], str) or Path(item['file']).name != item['file']
            or type(item['bytes']) is not int or item['bytes'] < 0
            or not isinstance(item['sha256'], str) or len(item['sha256']) != 64
            or any(c not in '0123456789abcdef' for c in item['sha256'])):
        raise ValueError('Invalid experiment asset')
    if 'gzip' in item:
        validate_asset(item['gzip'])
        if item['gzip']['file'] != item['file'] + '.gz':
            raise ValueError('Invalid compressed asset name')


def accepts_gzip(header):
    qualities = {}
    for token in header.lower().split(','):
        encoding, *parameters = token.strip().split(';')
        quality = 1.0
        for parameter in parameters:
            if parameter.strip().startswith('q='):
                try:
                    quality = float(parameter.strip()[2:])
                except ValueError:
                    quality = 0
        qualities[encoding.strip()] = quality
    return 0 < qualities.get('gzip', qualities.get('*', 0)) <= 1


_verified = OrderedDict()
_lock = Lock()


def asset_response(request, directory, item, filename, content_type):
    compressed = 'gzip' in item and accepts_gzip(request.headers.get('Accept-Encoding', ''))
    representation = item['gzip'] if compressed else item
    expected = filename + '.gz' if compressed else filename
    handle = None
    try:
        if representation['file'] != expected:
            raise ValueError('Unexpected asset name')
        base = Path(directory).resolve()
        path = (base / expected).resolve()
        if not path.is_relative_to(base):
            raise ValueError('Unsafe asset path')
        handle = path.open('rb')
        identity = signature(os.fstat(handle.fileno()))
        if identity[2] != representation['bytes']:
            raise ValueError('Asset size mismatch')
        key = (str(path), identity, representation['sha256'])
        with _lock:
            verified = key in _verified
            if verified:
                _verified.move_to_end(key)
        if not verified:
            digest = hashlib.file_digest(handle, 'sha256').hexdigest()
            if digest != representation['sha256'] or signature(os.fstat(handle.fileno())) != identity:
                raise ValueError('Asset changed or failed verification')
            with _lock:
                _verified[key] = True
                while len(_verified) > 256:
                    _verified.popitem(last=False)
        etag = f'"{representation["sha256"]}"'
        tags = parse_etags(request.headers.get('If-None-Match', ''))
        if '*' in tags or etag in [tag.removeprefix('W/') for tag in tags]:
            handle.close()
            response = HttpResponseNotModified()
        else:
            handle.seek(0)
            response = FileResponse(handle, content_type=content_type)
        response['ETag'] = etag
        response['Cache-Control'] = 'public, max-age=31536000, immutable'
        response['X-Content-Type-Options'] = 'nosniff'
        if compressed:
            response['Content-Encoding'] = 'gzip'
        patch_vary_headers(response, ['Accept-Encoding'])
        return response
    except DATA_ERRORS as error:
        if handle is not None:
            handle.close()
        raise Http404 from error
