#!/usr/bin/env python3
"""
Ensure every page loads the self-hosted webfont CSS.

Only 9 of 322 pages linked fonts/typekit.css, so the other 313 declared
font-family with no @font-face ever loaded. Local dev hid this because the
fonts are installed on the developer's machine and were silently picked up
as a same-name system fallback.

Normalises the existing links to a root-relative href at the same time: the
8 deep pages used ../../../../ which only resolves at that exact depth.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LINK = ('<link rel="stylesheet" type="text/css" '
        'href="/wp-content/themes/hello-theme-child-master/fonts/typekit.css">')

# Anchor: present in all 322 pages, and already where the 9 working pages
# put the link.
ANCHOR = re.compile(r'([ \t]*)<style id="wp-img-auto-sizes-contain-inline-css">')

# Any existing typekit link, whatever the relative depth, across the
# multi-line formatting in index.html and the single-line form elsewhere.
EXISTING = re.compile(
    r'[ \t]*<link\b[^>]*?href=["\'][^"\']*fonts/typekit\.css["\'][^>]*?/?>\s*',
    re.IGNORECASE | re.DOTALL,
)


def process(path):
    text = original = path.read_text(encoding='utf-8')

    text = EXISTING.sub('', text)

    m = ANCHOR.search(text)
    if not m:
        return 'NO ANCHOR'

    indent = m.group(1)
    text = text[:m.start()] + f'{indent}{LINK}\n' + text[m.start():]

    if text == original:
        return 'UNCHANGED'
    path.write_text(text, encoding='utf-8')
    return 'UPDATED'


def main():
    pages = sorted(
        p for p in ROOT.rglob('*.html')
        if 'wp-content' not in p.parts and p.name not in ('_header.html', '_footer.html')
    )
    print(f'Found {len(pages)} pages.\n')

    counts = {}
    for p in pages:
        status = process(p)
        counts[status] = counts.get(status, 0) + 1
        if status not in ('UPDATED', 'UNCHANGED'):
            print(f'  [{status}] {p.relative_to(ROOT)}')

    for k, v in sorted(counts.items()):
        print(f'  {k:12}: {v}')
    return 1 if counts.get('NO ANCHOR') else 0


if __name__ == '__main__':
    sys.exit(main())
