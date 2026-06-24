#!/usr/bin/env python3
"""Verify header/footer replacement is correct in sample pages."""
import re
from pathlib import Path

ROOT = Path(__file__).parent
BOM = '﻿'

hdr = (ROOT / '_header.html').read_text(encoding='utf-8-sig')
ftr = (ROOT / '_footer.html').read_text(encoding='utf-8-sig')

print(f'Master header length: {len(hdr)}')
print(f'Master footer length: {len(ftr)}')
print()

HEADER_RE = re.compile(
    r'<header\s[^>]*data-elementor-type=["\']header["\'][^>]*>',
    re.IGNORECASE,
)
FOOTER_RE = re.compile(
    r'<footer\s[^>]*data-elementor-type=["\']footer["\'][^>]*>',
    re.IGNORECASE,
)


def find_closing_tag(content, start, tag):
    open_re = re.compile(rf'<{tag}[\s>]', re.IGNORECASE)
    close_re = re.compile(rf'</{tag}>', re.IGNORECASE)
    depth, pos = 0, start
    while pos < len(content):
        om = open_re.search(content, pos)
        cm = close_re.search(content, pos)
        if om is None and cm is None:
            break
        if om is not None and (cm is None or om.start() < cm.start()):
            depth += 1
            pos = om.end()
        else:
            depth -= 1
            if depth == 0:
                return cm.end()
            pos = cm.end()
    return -1


samples = [
    ROOT / 'cyber-security-contact.html',
    ROOT / 'about-us' / 'index.html',
    ROOT / 'blog' / 'ai-and-automation' / 'ai-in-banking' / 'index.html',
    ROOT / 'our-services' / 'managed-services' / 'index.html',
]

all_ok = True
for p in samples:
    text = p.read_text(encoding='utf-8', errors='replace').replace(BOM, '')
    rel = p.relative_to(ROOT)
    issues = []

    hm = HEADER_RE.search(text)
    if hm:
        end = find_closing_tag(text, hm.start(), 'header')
        block = text[hm.start():end]
        if block != hdr:
            issues.append(f'header mismatch (len={len(block)}, expected={len(hdr)})')
    else:
        issues.append('no header found')

    fm = FOOTER_RE.search(text)
    if fm:
        end = find_closing_tag(text, fm.start(), 'footer')
        block = text[fm.start():end]
        if block != ftr:
            issues.append(f'footer mismatch (len={len(block)}, expected={len(ftr)})')
    else:
        issues.append('no footer found')

    boms = text.count(BOM)
    if boms:
        issues.append(f'stray BOM x{boms}')

    if issues:
        all_ok = False
        print(f'  FAIL  {rel}')
        for i in issues:
            print(f'         - {i}')
    else:
        print(f'  OK    {rel}')

print()
print('All checks passed!' if all_ok else 'SOME CHECKS FAILED')
