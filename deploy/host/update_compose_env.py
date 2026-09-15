"""Update the release pair without discarding existing Compose configuration."""
import os
from pathlib import Path
import sys


def updated(text, version, port=None):
    values = {'IMAGE_TAG': version, 'DATA_VERSION': version}
    if port:
        values['HOST_PORT'] = port
    seen, lines = set(), []
    for line in text.splitlines():
        key = line.partition('=')[0].strip()
        if key in values:
            lines.append(f'{key}={values[key]}')
            seen.add(key)
        else:
            lines.append(line)
            if key == 'HOST_PORT':
                seen.add(key)
    for key, value in values.items():
        if key not in seen:
            lines.append(f'{key}={value}')
    if 'HOST_PORT' not in seen and 'HOST_PORT' not in values:
        lines.append('HOST_PORT=8014')
    return '\n'.join(lines)+'\n'


if __name__ == '__main__':
    version, target = sys.argv[1:]
    source = Path('.env')
    Path(target).write_text(updated(source.read_text() if source.exists() else '',
                                    version, os.environ.get('HOST_PORT')))
