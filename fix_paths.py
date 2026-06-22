#!/usr/bin/env python3
"""
fix_paths.py
Converts relative URLs in _header.html and _footer.html to root-relative
absolute paths so nav links, images, and srcsets work correctly from any
page depth (e.g. /our-solutions/av-collaboration/ doesn't mis-resolve them).

Run once, then re-run build_header_footer.py to push the fix to all pages.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent

# URL prefixes that must NOT be modified.
SKIP = ('/', 'http://', 'https://', '//', '#', 'mailto:', 'tel:', 'javascript:', 'data:')


def make_abs(url: str) -> str:
    """Prefix a relative URL with / unless it already is absolute."""
    url = url.strip()
    if not url or any(url.startswith(p) for p in SKIP):
        return url
    return '/' + url


def fix_href(m: re.Match) -> str:
    return f'href="{make_abs(m.group(1))}"'


def fix_src(m: re.Match) -> str:
    return f'src="{make_abs(m.group(1))}"'


def fix_srcset(m: re.Match) -> str:
    """
    srcset values look like:  "img.png 300w, img-big.png 768w"
    Each comma-separated token is: <url> [descriptor]
    """
    raw = m.group(1)
    fixed_parts = []
    for part in raw.split(','):
        tokens = part.strip().split()
        if tokens:
            tokens[0] = make_abs(tokens[0])
        fixed_parts.append(' '.join(tokens))
    return 'srcset="' + ', '.join(fixed_parts) + '"'


def fix_file(path: Path) -> None:
    text = path.read_text(encoding='utf-8-sig')   # strips BOM on read
    original = text

    text = re.sub(r'href="([^"]*)"',   fix_href,   text)
    text = re.sub(r'src="([^"]*)"',    fix_src,    text)
    text = re.sub(r'srcset="([^"]*)"', fix_srcset, text)

    if text != original:
        path.write_text(text, encoding='utf-8')   # write without BOM
        changes = sum(
            1 for a, b in zip(original.splitlines(), text.splitlines()) if a != b
        )
        print(f'  Fixed  {path.name}  (~{changes} lines changed)')
    else:
        print(f'  No change: {path.name}')


if __name__ == '__main__':
    print('Fixing paths in master header/footer files...\n')
    fix_file(ROOT / '_header.html')
    fix_file(ROOT / '_footer.html')
    print('\nDone. Now run:  python build_header_footer.py')
