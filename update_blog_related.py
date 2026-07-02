#!/usr/bin/env python3
"""Convert 'Other articles that might interest you' into randomized,
self-excluding 'Related blogs' cards on every blog post page."""
import json
import random
from pathlib import Path

from blog_related_lib import (
    build_card_html,
    extract_post_data,
    find_srcset,
    replace_related_section,
)

ROOT = Path(__file__).parent
BLOG = ROOT / "blog"
OUT_JSON = ROOT / "data" / "all-blog-posts.json"
PREFIX = "../../../"


def target_files():
    return [
        p for p in sorted(BLOG.glob("*/*/index.html"))
        if p.parent.parent.name != "page"
    ]


def build_database(files):
    posts = []
    skipped = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        data = extract_post_data(text)
        if data is None:
            skipped.append(path)
            continue
        url = path.relative_to(ROOT).as_posix()
        srcset = find_srcset(data["image"], data["width"], ROOT)
        posts.append({**data, "url": url, "srcset": srcset})
    posts.sort(key=lambda p: p["id"])
    return posts, skipped


def main():
    files = target_files()
    posts, skipped = build_database(files)

    OUT_JSON.parent.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Scanned {len(files)} pages, extracted {len(posts)} posts, skipped {len(skipped)}")
    for p in skipped:
        print(f"  SKIPPED (missing data): {p.relative_to(ROOT)}")

    updated = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        own_url = path.relative_to(ROOT).as_posix()
        candidates = [p for p in posts if p["url"] != own_url]
        if len(candidates) < 3:
            print(f"  SKIPPED (not enough candidates): {own_url}")
            continue
        chosen = random.sample(candidates, 3)
        cards_html = "\n".join(build_card_html(p, PREFIX) for p in chosen)
        try:
            new_text = replace_related_section(text, cards_html)
        except ValueError as exc:
            print(f"  SKIPPED ({exc}): {own_url}")
            continue
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            updated += 1

    print(f"Updated {updated} of {len(files)} pages")


if __name__ == "__main__":
    main()
