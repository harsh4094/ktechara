"""
Generate blog/blog-posts.json — extract every blog card from all 14 listing
pages so blog-filter.js can filter across all posts without a backend.
"""
import re, os, json
from urllib.parse import urljoin

BASE  = r"d:\TrainingGround\BHAVIK-PROJECTS\ktechara\blog"
MARKER = '<div data-elementor-type="loop-item"'

FILES = [(os.path.join(BASE, "index.html"), "http://x/blog/")]
for i in range(2, 15):
    p = os.path.join(BASE, "page", str(i), "index.html")
    if os.path.exists(p):
        FILES.append((p, f"http://x/blog/page/{i}/"))


def abs_url(href, base):
    if not href:
        return ""
    return urljoin(base, href).replace("http://x", "")


def find_div_end(content, start):
    depth, i = 0, start
    while i < len(content):
        if content[i:i+4] == "<div":
            depth += 1
            j = content.find(">", i)
            i = j + 1 if j != -1 else len(content)
        elif content[i:i+6] == "</div>":
            depth -= 1
            i += 6
            if depth == 0:
                return i
        else:
            i += 1
    return len(content)


seen, posts = set(), []

for filepath, base_url in FILES:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    pos = 0
    while True:
        start = content.find(MARKER, pos)
        if start == -1:
            break
        end  = find_div_end(content, start)
        card = content[start:end]
        pos  = end

        # Post ID (deduplicate across pages)
        id_m = re.search(r"\bpost-(\d+)\b", card)
        if not id_m:
            continue
        pid = int(id_m.group(1))
        if pid in seen:
            continue
        seen.add(pid)

        # Class string → taxonomy
        cls_m = re.match(r'<div[^>]+class="([^"]*)"', card)
        classes = cls_m.group(1).split() if cls_m else []
        insight_types  = [c[len("insights-type-"):]  for c in classes
                          if c.startswith("insights-type-") and c not in
                          ("insights-type-events", "insights-type-news", "insights-type-newsletter-exclusive")]
        if not insight_types:
            continue  # skip non-blog posts
        business_needs = [c[len("business-need-"):]  for c in classes
                          if c.startswith("business-need-") and not c.endswith("-various")]
        services       = [c[len("service-"):]        for c in classes
                          if c.startswith("service-") and not c.endswith("-various")]
        categories     = [c[len("primary-category-"):] for c in classes
                          if c.startswith("primary-category-") and not c.endswith("-various")]

        # Title & URL
        t_m = re.search(
            r'class="elementor-heading-title[^"]*"[^>]*><a[^>]+href="([^"]*)"[^>]*>(.*?)</a>',
            card, re.DOTALL
        )
        if not t_m:
            continue
        url_raw = t_m.group(1)
        title   = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t_m.group(2))).strip()
        url     = abs_url(url_raw, base_url)

        # Featured image — find first wp-content/uploads src in the card
        img_m = re.search(r'src="([^"]*wp-content/uploads[^"]*)"', card)
        image = abs_url(img_m.group(1), base_url) if img_m else ""

        posts.append({
            "id":            pid,
            "title":         title,
            "url":           url,
            "image":         image,
            "insightTypes":  insight_types,
            "businessNeeds": business_needs,
            "services":      services,
            "categories":    categories,
        })

print(f"Extracted {len(posts)} unique posts")

out = os.path.join(BASE, "blog-posts.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(posts, f, ensure_ascii=False, indent=2)
print(f"Written to: {out}")

all_it  = sorted({v for p in posts for v in p["insightTypes"]})
all_bn  = sorted({v for p in posts for v in p["businessNeeds"]})
all_svc = sorted({v for p in posts for v in p["services"]})
print(f"Insight types  : {all_it}")
print(f"Business needs : {all_bn}")
print(f"Services       : {all_svc}")
