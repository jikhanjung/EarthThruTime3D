"""Convert only plain/lowstand legacy river fields; ice lakes must be regenerated."""
import argparse
from pathlib import Path
from PIL import Image


def migrate_plain_fields(directory):
    files = sorted(set(directory.glob('*-rivers.png')) | set(directory.glob('*-rivers-low.png')))
    converted = 0
    for path in files:
        with Image.open(path) as source:
            source.load()
            if source.size != (2048, 1024):
                raise ValueError(f'Unexpected river field size: {path}')
            if source.mode == 'RGB':
                if any(source.getchannel(c).getextrema() != (0, 0) for c in ('G', 'B')):
                    raise ValueError(f'Plain fields must have empty green/blue channels: {path}')
                continue
            if source.mode != 'L':
                raise ValueError(f'Expected legacy L or migrated RGB: {path}')
            zero = Image.new('L', source.size)
            result = Image.merge('RGB', (source, zero, zero))
        temporary = path.with_suffix('.rgb.tmp')
        try:
            result.save(temporary, format='PNG')
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        converted += 1
    return converted


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[1]/'data/derived/paleodem')
    args = parser.parse_args()
    print(f'Converted {migrate_plain_fields(args.directory)} plain/lowstand river fields; ice fields untouched.')
