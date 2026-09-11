#!/usr/bin/env python3
"""
Rename every reference to the unlicensed Adelle fonts to the open-source
replacements now self-hosted in fonts/typekit.css.

  adelle-sans-ultra-thin, "Adelle Sans Ultra Thin" -> Source Sans 3
  adelle-sans, "Adelle Sans"                       -> Source Sans 3
  adelle-ultrathin, "Adelle Ultrathin"              -> Zilla Slab
  adelle, "Adelle"                                  -> Zilla Slab

Longest token first so "adelle" cannot corrupt "adelle-sans" mid-substitution.
Case-insensitive matching, case-preserving-ish replacement (lower stays
lower/hyphenated form maps to the real family name; any capitalised /
quoted display form maps to the same family name too, since CSS
font-family names are not hyphenated once real).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REPLACEMENTS = [
    (re.compile(r'adelle-sans-ultra-thin', re.IGNORECASE), 'Source Sans 3'),
    (re.compile(r'adelle sans ultra thin', re.IGNORECASE), 'Source Sans 3'),
    (re.compile(r'adelle-ultrathin', re.IGNORECASE), 'Zilla Slab'),
    (re.compile(r'adelle ultrathin', re.IGNORECASE), 'Zilla Slab'),
    (re.compile(r'adelle-sans', re.IGNORECASE), 'Source Sans 3'),
    (re.compile(r'adelle sans', re.IGNORECASE), 'Source Sans 3'),
    (re.compile(r'adelle', re.IGNORECASE), 'Zilla Slab'),
]

EXTENSIONS = ('.html', '.css')
SKIP_NAMES = {'rename_adelle_fonts.py'}


def process(path: Path) -> int:
    text = original = path.read_text(encoding='utf-8', errors='replace')
    changes = 0
    for pattern, repl in REPLACEMENTS:
        text, n = pattern.subn(repl, text)
        changes += n
    if text != original:
        path.write_text(text, encoding='utf-8')
    return changes


def main():
    total_files = 0
    total_refs = 0
    for path in ROOT.rglob('*'):
        if path.name in SKIP_NAMES:
            continue
        if path.suffix.lower() not in EXTENSIONS:
            continue
        if not path.is_file():
            continue
        n = process(path)
        if n:
            total_files += 1
            total_refs += n
            print(f'  [{n:4d} refs]  {path.relative_to(ROOT)}')

    print(f'\nDone. {total_refs} references updated across {total_files} files.')


if __name__ == '__main__':
    main()
