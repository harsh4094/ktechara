#!/usr/bin/env python3
"""Point dead href="#" anchors in 'Related blogs' cards on non-blog pages
to their blog post URLs, using the post id baked into each card's class."""
import json
import re
from pathlib import Path

from blog_related_lib import _find_div_end, build_card_html

ROOT = Path(__file__).parent
MARKER = 'data-elementor-type="loop-item"'

# Cards referencing blog posts that no longer exist -> swap in a real post.
# key: (page, card index among loop-items), value: replacement post url
DEAD_CARD_SWAPS = {
    ("our-services/managed-it-services/index.html", 2):
        "blog/azure-and-cloud/the-advania-guide-to-azure-part-2-calculating-total-cost-of-ownership-in-azure/index.html",
    ("our-services/unified-communications/index.html", 0):
        "blog/modern-work/microsoft-teams-collaboration-features/index.html",
    ("our-services/unified-communications/unified-communications-and-collaboration/index.html", 0):
        "blog/modern-work/microsoft-teams-collaboration-features/index.html",
}


def swap_dead_cards(text, rel, posts):
    swaps = {i: url for (page, i), url in DEAD_CARD_SWAPS.items() if page == rel}
    if not swaps:
        return text, 0
    prefix = "../" * rel.count("/")
    post_by_url = {p["url"]: p for p in posts}
    # collect card block spans (start of enclosing <div ... loop-item ...>)
    spans = []
    pos = 0
    while (i := text.find(MARKER, pos)) != -1:
        start = text.rfind("<div", 0, i)
        end = _find_div_end(text, start)
        spans.append((start, end))
        pos = end
    done = 0
    for idx in sorted(swaps, reverse=True):
        start, end = spans[idx]
        card = build_card_html(post_by_url[swaps[idx]], prefix).lstrip()
        text = text[:start] + card + text[end:]
        done += 1
    return text, done

PAGES = [
    p for p in ROOT.rglob("index.html")
    if "Related blogs" in p.read_text(encoding="utf-8", errors="ignore")
    and not p.relative_to(ROOT).as_posix().startswith(("blog/", "wp-content/"))
    and p != ROOT / "index.html"
]

posts = json.loads((ROOT / "data" / "all-blog-posts.json").read_text(encoding="utf-8"))
url_by_id = {p["id"]: "/" + p["url"].removesuffix("index.html") for p in posts}


def fix(text):
    parts = text.split(MARKER)
    fixed = missing = 0
    for i in range(1, len(parts)):
        m = re.search(r"\bpost-(\d+)\b", parts[i])
        url = url_by_id.get(int(m.group(1))) if m else None
        if not url:
            missing += 1
            continue
        n = parts[i].count('href="#"')
        parts[i] = parts[i].replace('href="#"', f'href="{url}"')
        fixed += n
    return MARKER.join(parts), fixed, missing


total = 0
for page in sorted(PAGES):
    rel = page.relative_to(ROOT).as_posix()
    text = page.read_text(encoding="utf-8")
    new, swapped = swap_dead_cards(text, rel, posts)
    new, fixed, missing = fix(new)
    note = f" ({missing} card(s) not in blog db)" if missing else ""
    if swapped:
        note += f" ({swapped} dead card(s) replaced)"
    print(f"{rel}: {fixed} links fixed{note}")
    if new != text:
        page.write_text(new, encoding="utf-8")
        total += fixed + swapped
print(f"Total: {total} fixes across {len(PAGES)} pages")

if __name__ == "__main__":
    pass
