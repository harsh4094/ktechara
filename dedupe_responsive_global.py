#!/usr/bin/env python3
"""
Collapse the repeated <style id="responsive-global"> block down to one copy
per page.

build_header_footer.py appends this block on each run rather than replacing
it, because the block sits outside the <header> element it matches on. Since
_header.html has been rebaked into all 322 pages many times, each page ended
up with up to ~19 stacked copies (~14KB of dead CSS per page). The script
itself still has this bug; this is a one-off cleanup, not a fix to the root
cause.

Keeps the LAST occurrence (the most complete/current content, since later
_header.html revisions added more rules to the block) and removes the rest.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

BLOCK = re.compile(
    r'[ \t]*<style id="responsive-global">.*?</style>\n?',
    re.DOTALL,
)


def process(path: Path) -> int:
    text = original = path.read_text(encoding='utf-8', errors='replace')
    matches = list(BLOCK.finditer(text))
    if len(matches) <= 1:
        return 0

    keep = matches[-1].group(0)
    # Remove all occurrences, then reinsert one copy at the first occurrence's position.
    first_start = matches[0].start()
    new_text = BLOCK.sub('', text)
    new_text = new_text[:first_start] + keep + new_text[first_start:]

    if new_text != original:
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(new_text, encoding='utf-8')
        tmp.replace(path)
    return len(matches) - 1


def main():
    total_files = 0
    total_removed = 0
    for path in sorted(ROOT.rglob('*.html')):
        if 'wp-content' in path.parts:
            continue
        n = process(path)
        if n:
            total_files += 1
            total_removed += n
            print(f'  [-{n:2d} dupes]  {path.relative_to(ROOT)}')

    print(f'\nDone. Removed {total_removed} duplicate blocks across {total_files} files.')


if __name__ == '__main__':
    main()
