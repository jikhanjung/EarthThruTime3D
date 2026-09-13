#!/usr/bin/env python3
"""Compile locale/*/LC_MESSAGES/django.po into the .mo files Django reads.

Django's own compilemessages needs GNU msgfmt, which neither the development host nor
the python:slim image carries. The .mo format is small enough to write directly: a
header, two sorted tables of (length, offset) pairs, then the strings. Plural entries
join their forms with NUL, as msgfmt does. The .mo files are build products and are not
committed; run this after editing a .po, and the build does it for the image.
"""
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def unquote(line):
    body = line[line.index('"') + 1:line.rindex('"')]
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t', '"': '"', '\\': '\\'}[m.group(1)], body)


def parse(text):
    """Entries as (msgid, translation) with plural forms joined by NUL."""
    entries, current, key = [], {}, None
    def flush():
        if 'msgid' in current:
            if 'msgid_plural' in current:
                forms = [current[f'msgstr[{i}]'] for i in range(len([k for k in current if k.startswith('msgstr[')]))]
                entries.append((current['msgid'] + '\0' + current['msgid_plural'], '\0'.join(forms)))
            else:
                entries.append((current['msgid'], current.get('msgstr', '')))
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('"'):
            current[key] += unquote(line)
            continue
        keyword, _, rest = line.partition(' ')
        if keyword == 'msgid':
            flush()
            current = {}
        key = keyword
        current[key] = unquote(rest)
    flush()
    return entries


def compile_po(source, target):
    entries = sorted(parse(source.read_text(encoding='utf-8')))
    ids = b''.join(e[0].encode('utf-8') + b'\0' for e in entries)
    strs = b''.join(e[1].encode('utf-8') + b'\0' for e in entries)
    count = len(entries)
    ids_offset = 7 * 4 + count * 16
    strs_offset = ids_offset + len(ids)
    id_table, str_table, i_pos, s_pos = [], [], 0, 0
    for msgid, msgstr in entries:
        i_len, s_len = len(msgid.encode('utf-8')), len(msgstr.encode('utf-8'))
        id_table += [i_len, ids_offset + i_pos]
        str_table += [s_len, strs_offset + s_pos]
        i_pos += i_len + 1
        s_pos += s_len + 1
    header = struct.pack('<7I', 0x950412de, 0, count, 7 * 4, 7 * 4 + count * 8, 0, 0)
    target.write_bytes(header + struct.pack(f'<{count * 2}I', *id_table)
                       + struct.pack(f'<{count * 2}I', *str_table) + ids + strs)
    return count


def main():
    compiled = 0
    for po in sorted((ROOT / 'locale').glob('*/LC_MESSAGES/django.po')):
        count = compile_po(po, po.with_suffix('.mo'))
        print(f'{po.relative_to(ROOT)}: {count} entries')
        compiled += 1
    if not compiled:
        sys.exit('No .po files under locale/.')


if __name__ == '__main__':
    main()
