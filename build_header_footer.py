#!/usr/bin/env python3
"""
build_header_footer.py
----------------------
Replaces the inline <header> and <footer> blocks in every HTML page
with the canonical content from _header.html and _footer.html.

Usage:
    python build_header_footer.py

Run this script whenever you update _header.html or _footer.html.
All HTML files will be updated in a few seconds.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent

# UTF-8 BOM character — removed from master files on read and scrubbed from
# pages to clean up any stray BOMs injected by earlier tool runs.
BOM = '﻿'


def find_closing_tag(content: str, start: int, tag: str) -> int:
    """
    Starting at `start` (the opening tag), walks forward counting nested
    open/close pairs and returns the position immediately after the matching
    closing tag. Returns -1 if not found.
    """
    open_re = re.compile(rf'<{tag}[\s>]', re.IGNORECASE)
    close_re = re.compile(rf'</{tag}>', re.IGNORECASE)
    depth = 0
    pos = start

    while pos < len(content):
        open_m = open_re.search(content, pos)
        close_m = close_re.search(content, pos)

        if open_m is None and close_m is None:
            break

        if open_m is not None and (close_m is None or open_m.start() < close_m.start()):
            depth += 1
            pos = open_m.end()
        else:
            depth -= 1
            if depth == 0:
                return close_m.end()
            pos = close_m.end()

    return -1


def process_file(path: Path, header_html: str, footer_html: str) -> tuple:
    """
    Replaces the Elementor header/footer blocks in one HTML file.
    Returns (was_modified: bool, status: str).
    """
    try:
        # Read as plain UTF-8; universal newlines normalises CRLF → LF.
        raw = path.read_text(encoding='utf-8', errors='replace')
    except Exception as exc:
        return False, f'READ ERROR: {exc}'

    # Scrub any stray BOMs (e.g. from a previous bad run) anywhere in the file.
    text = raw.replace(BOM, '')
    original = text

    # ── Header ──────────────────────────────────────────────────────────────
    header_re = re.compile(
        r'<header\s[^>]*data-elementor-type=["\']header["\'][^>]*>',
        re.IGNORECASE,
    )
    hm = header_re.search(text)
    if hm:
        end = find_closing_tag(text, hm.start(), 'header')
        if end != -1:
            text = text[: hm.start()] + header_html + text[end:]

    # ── Footer ──────────────────────────────────────────────────────────────
    footer_re = re.compile(
        r'<footer\s[^>]*data-elementor-type=["\']footer["\'][^>]*>',
        re.IGNORECASE,
    )
    fm = footer_re.search(text)
    if fm:
        end = find_closing_tag(text, fm.start(), 'footer')
        if end != -1:
            text = text[: fm.start()] + footer_html + text[end:]

    if text == original:
        return False, 'UNCHANGED'

    try:
        path.write_text(text, encoding='utf-8')
        return True, 'UPDATED'
    except Exception as exc:
        return False, f'WRITE ERROR: {exc}'


def main() -> None:
    header_path = ROOT / '_header.html'
    footer_path = ROOT / '_footer.html'

    for p in (header_path, footer_path):
        if not p.exists():
            print(f'ERROR: {p} not found.')
            sys.exit(1)

    # utf-8-sig strips the UTF-8 BOM if present.
    header_html = header_path.read_text(encoding='utf-8-sig')
    footer_html = footer_path.read_text(encoding='utf-8-sig')

    skip = {header_path.resolve(), footer_path.resolve()}
    html_files = sorted(
        p for p in ROOT.rglob('*.html') if p.resolve() not in skip
    )

    print(f'Found {len(html_files)} HTML files. Processing...\n')

    updated = unchanged = errors = 0

    for p in html_files:
        modified, status = process_file(p, header_html, footer_html)
        rel = p.relative_to(ROOT)
        if modified:
            updated += 1
            print(f'  [UPDATED]   {rel}')
        elif 'ERROR' in status:
            errors += 1
            print(f'  [ERROR]     {rel}: {status}')

    unchanged = len(html_files) - updated - errors

    print(f'\n{"-" * 50}')
    print(f'  Updated  : {updated}')
    print(f'  Unchanged: {unchanged}')
    print(f'  Errors   : {errors}')
    print(f'  Total    : {len(html_files)}')
    print(f'{"-" * 50}')


if __name__ == '__main__':
    main()
