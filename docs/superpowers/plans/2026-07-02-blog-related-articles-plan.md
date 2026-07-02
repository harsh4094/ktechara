# Blog "Related blogs" Section Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded "Other articles that might interest you" News/Event cards on all 180 blog post pages with 3 randomly-picked, self-excluding "Related blogs" cards, matching the homepage's existing "Related blogs" component.

**Architecture:** A pure, unit-tested library module (`blog_related_lib.py`) provides the text-processing functions (title cleanup, post-data extraction, srcset discovery, card HTML generation, section replacement). A thin driver script (`update_blog_related.py`) walks the 180 blog post files, builds a JSON database of all posts, then rewrites each page's related-cards section using the library functions.

**Tech Stack:** Python 3 standard library only (`re`, `pathlib`, `json`, `random`, `unittest`) — no new dependencies, matching the rest of the repo's automation scripts.

## Global Constraints

- Scope is exactly the 180 pages matching `blog/<category>/<slug>/index.html` (i.e. `blog/*/*/index.html` where the grandparent directory is not `page`). Podcast pages, the stray root page, and pagination pages are untouched.
- `data/blog-posts.json` (used by the homepage and `our-solutions` pages) must not be modified.
- New database file: `data/all-blog-posts.json`.
- No new third-party dependencies (stdlib only).
- Heading text changes from "Other articles that might interest you" to "Related blogs" on every target page.
- Each page's own post must never appear among its own 3 related cards.
- Card wrapper class uses `insights-type-blog` (not `insights-type-news` / `insights-type-events`).
- Re-running the driver script must be safe and simply reshuffle picks (no accumulating state).

---

### Task 1: Title cleanup and post-data extraction

**Files:**
- Create: `blog_related_lib.py`
- Test: `tests/test_blog_related_lib.py`

**Interfaces:**
- Produces: `clean_title(raw_title: str) -> str`
- Produces: `extract_post_data(html_text: str) -> dict | None` — returns `{"id": int, "title": str, "image": str, "width": int, "height": int}` or `None` if required fields (`postid-<N>` body class, `<title>`, `og:image`) are missing.

- [ ] **Step 1: Write the failing tests**

Create `tests/__init__.py` (empty file, so `tests` is importable as a package):

```python
```

Create `tests/test_blog_related_lib.py`:

```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from blog_related_lib import clean_title, extract_post_data


class CleanTitleTests(unittest.TestCase):
    def test_strips_k_techara_suffix(self):
        self.assertEqual(clean_title("How Power Apps work - K Techara"), "How Power Apps work")

    def test_strips_k_techara_uk_suffix(self):
        self.assertEqual(
            clean_title("Cyber security AI from Inspire’s news - K Techara UK"),
            "Cyber security AI from Inspire’s news",
        )

    def test_strips_en_dash_suffix(self):
        self.assertEqual(
            clean_title("Which digital tools are best – K Techara"),
            "Which digital tools are best",
        )

    def test_no_suffix_is_left_unchanged(self):
        self.assertEqual(clean_title("Staff Turnover Risk"), "Staff Turnover Risk")

    def test_collapses_multiline_whitespace(self):
        raw = "\n      How to build a relationship with an AI\n    "
        self.assertEqual(clean_title(raw), "How to build a relationship with an AI")


class ExtractPostDataTests(unittest.TestCase):
    def make_html(self, postid='postid-28004', title='<title>How to build a relationship with an AI</title>',
                  og_image='<meta property="og:image" content="/wp-content/uploads/2024/03/pic.png" />',
                  og_width='<meta property="og:image:width" content="1200" />',
                  og_height='<meta property="og:image:height" content="600" />'):
        return f'''<!doctype html>
<html><head>
{title}
{og_image}
{og_width}
{og_height}
</head><body class="wp-singular single {postid} single-format-standard">
</body></html>'''

    def test_extracts_all_fields(self):
        data = extract_post_data(self.make_html())
        self.assertEqual(data, {
            "id": 28004,
            "title": "How to build a relationship with an AI",
            "image": "/wp-content/uploads/2024/03/pic.png",
            "width": 1200,
            "height": 600,
        })

    def test_defaults_width_height_when_missing(self):
        html = self.make_html(og_width='', og_height='')
        data = extract_post_data(html)
        self.assertEqual(data["width"], 1200)
        self.assertEqual(data["height"], 600)

    def test_handles_multiline_title_tag(self):
        html = self.make_html(title='<title>\n      How Power Apps work - K Techara\n    </title>')
        data = extract_post_data(html)
        self.assertEqual(data["title"], "How Power Apps work")

    def test_returns_none_when_postid_missing(self):
        html = self.make_html(postid='no-post-id-here')
        self.assertIsNone(extract_post_data(html))

    def test_returns_none_when_og_image_missing(self):
        html = self.make_html(og_image='')
        self.assertIsNone(extract_post_data(html))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_blog_related_lib -v`
Expected: `ModuleNotFoundError: No module named 'blog_related_lib'` (or import error) — the module doesn't exist yet.

- [ ] **Step 3: Create `blog_related_lib.py` with the implementation**

```python
"""Shared text-processing helpers for converting blog post 'related articles'
sections from hardcoded News/Event cards into randomized Blog cards."""
import re

TITLE_SUFFIX_RE = re.compile(r"\s*[-–]\s*K\s*Techara(\s*UK)?\s*$", re.IGNORECASE)
POSTID_RE = re.compile(r"postid-(\d+)")
TITLE_TAG_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL)
OG_IMAGE_RE = re.compile(r'property="og:image"\s+content="([^"]+)"')
OG_IMAGE_WIDTH_RE = re.compile(r'property="og:image:width"\s+content="([^"]+)"')
OG_IMAGE_HEIGHT_RE = re.compile(r'property="og:image:height"\s+content="([^"]+)"')


def clean_title(raw_title: str) -> str:
    collapsed = re.sub(r"\s+", " ", raw_title).strip()
    return TITLE_SUFFIX_RE.sub("", collapsed).strip()


def extract_post_data(html_text: str) -> dict | None:
    postid_m = POSTID_RE.search(html_text)
    title_m = TITLE_TAG_RE.search(html_text)
    image_m = OG_IMAGE_RE.search(html_text)
    if not (postid_m and title_m and image_m):
        return None

    width_m = OG_IMAGE_WIDTH_RE.search(html_text)
    height_m = OG_IMAGE_HEIGHT_RE.search(html_text)

    return {
        "id": int(postid_m.group(1)),
        "title": clean_title(title_m.group(1)),
        "image": image_m.group(1),
        "width": int(width_m.group(1)) if width_m else 1200,
        "height": int(height_m.group(1)) if height_m else 600,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_blog_related_lib -v`
Expected: `OK` with 10 tests run (5 `CleanTitleTests` + 5 `ExtractPostDataTests`), 0 failures.

- [ ] **Step 5: Commit**

```bash
git add blog_related_lib.py tests/__init__.py tests/test_blog_related_lib.py
git commit -m "feat(blog): add title cleanup and post-data extraction helpers"
```

---

### Task 2: Srcset discovery from on-disk image variants

**Files:**
- Modify: `blog_related_lib.py`
- Test: `tests/test_blog_related_lib.py`

**Interfaces:**
- Consumes: nothing from Task 1 directly (independent function).
- Produces: `find_srcset(image_path: str, width: int, project_root) -> str | None` — `image_path` is a root-relative path starting with `/` (e.g. `/wp-content/uploads/2024/03/pic.png`); `project_root` is a `pathlib.Path`. Returns a comma-separated `srcset` string (root-relative paths, each `"{path} {width}w"`, ascending by width, including the base image itself) or `None` if no resized sibling files exist on disk.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_blog_related_lib.py` (add import and new test class):

```python
import tempfile
from pathlib import Path

from blog_related_lib import clean_title, extract_post_data, find_srcset
```

(Replace the existing `from blog_related_lib import clean_title, extract_post_data` line with the line above.)

```python
class FindSrcsetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.img_dir = self.root / "wp-content" / "uploads" / "2024" / "03"
        self.img_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_none_when_no_variants_exist(self):
        (self.img_dir / "pic.png").write_bytes(b"x")
        result = find_srcset("/wp-content/uploads/2024/03/pic.png", 1200, self.root)
        self.assertIsNone(result)

    def test_builds_srcset_from_variants_ascending_by_width(self):
        (self.img_dir / "pic.png").write_bytes(b"x")
        (self.img_dir / "pic-1024x512.png").write_bytes(b"x")
        (self.img_dir / "pic-300x150.png").write_bytes(b"x")
        (self.img_dir / "pic-768x384.png").write_bytes(b"x")
        result = find_srcset("/wp-content/uploads/2024/03/pic.png", 1200, self.root)
        self.assertEqual(
            result,
            "/wp-content/uploads/2024/03/pic-300x150.png 300w, "
            "/wp-content/uploads/2024/03/pic-768x384.png 768w, "
            "/wp-content/uploads/2024/03/pic-1024x512.png 1024w, "
            "/wp-content/uploads/2024/03/pic.png 1200w",
        )

    def test_ignores_unrelated_files_in_same_directory(self):
        (self.img_dir / "pic.png").write_bytes(b"x")
        (self.img_dir / "other-picture-300x150.png").write_bytes(b"x")
        result = find_srcset("/wp-content/uploads/2024/03/pic.png", 1200, self.root)
        self.assertIsNone(result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_blog_related_lib -v`
Expected: `AttributeError` / `ImportError` — `find_srcset` doesn't exist yet.

- [ ] **Step 3: Implement `find_srcset` in `blog_related_lib.py`**

Add to `blog_related_lib.py` (near the top, add `import re` is already present; add):

```python
from pathlib import Path


def find_srcset(image_path: str, width: int, project_root) -> str | None:
    rel = image_path.lstrip("/")
    full_path = Path(project_root) / rel
    base, ext = full_path.stem, full_path.suffix

    variants = {(image_path, width)}
    pattern = re.compile(rf"^{re.escape(base)}-(\d+)x(\d+){re.escape(ext)}$")
    for sibling in full_path.parent.glob(f"{base}-*x*{ext}"):
        m = pattern.match(sibling.name)
        if not m:
            continue
        sibling_width = int(m.group(1))
        rel_variant = "/" + sibling.relative_to(project_root).as_posix()
        variants.add((rel_variant, sibling_width))

    if len(variants) == 1:
        return None

    ordered = sorted(variants, key=lambda t: t[1])
    return ", ".join(f"{path} {w}w" for path, w in ordered)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_blog_related_lib -v`
Expected: `OK` with 13 tests run, 0 failures.

- [ ] **Step 5: Commit**

```bash
git add blog_related_lib.py tests/test_blog_related_lib.py
git commit -m "feat(blog): add srcset discovery for related-post images"
```

---

### Task 3: Card HTML generation

**Files:**
- Modify: `blog_related_lib.py`
- Test: `tests/test_blog_related_lib.py`

**Interfaces:**
- Consumes: a post `dict` shaped like Task 1's `extract_post_data` output plus a `url: str` (root-relative, no leading slash, e.g. `"blog/agility/building-relationship-ai/index.html"`) and `srcset: str | None` (Task 2's `find_srcset` output).
- Produces: `build_card_html(post: dict, prefix: str) -> str` — a single loop-item `<div>` block as a string, indented to match the existing page markup.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_blog_related_lib.py` (update the import line to add `build_card_html`):

```python
from blog_related_lib import clean_title, extract_post_data, find_srcset, build_card_html
```

```python
class BuildCardHtmlTests(unittest.TestCase):
    def test_card_without_srcset(self):
        post = {
            "id": 28004,
            "title": "How to build a relationship with an AI",
            "url": "blog/agility/building-relationship-ai/index.html",
            "image": "/wp-content/uploads/2024/03/pic.png",
            "width": 1200,
            "height": 600,
            "srcset": None,
        }
        html = build_card_html(post, "../../../")
        self.assertIn('e-loop-item-28004 post-28004', html)
        self.assertIn('insights-type-blog', html)
        self.assertIn('href="../../../blog/agility/building-relationship-ai/index.html"', html)
        self.assertIn('>How to build a relationship with an AI<', html)
        self.assertIn('href="../../../blog/index.html"', html)
        self.assertIn('>Blog<', html)
        self.assertIn('src="../../../wp-content/uploads/2024/03/pic.png"', html)
        self.assertIn('width="1200"', html)
        self.assertIn('height="600"', html)
        self.assertNotIn('srcset=', html)

    def test_card_with_srcset_prefixes_every_entry(self):
        post = {
            "id": 33690,
            "title": "AI &amp; the enterprise",
            "url": "blog/data/ai-and-the-enterprise/index.html",
            "image": "/wp-content/uploads/2024/03/pic.png",
            "width": 1200,
            "height": 600,
            "srcset": "/wp-content/uploads/2024/03/pic-300x150.png 300w, /wp-content/uploads/2024/03/pic.png 1200w",
        }
        html = build_card_html(post, "../../../")
        self.assertIn(
            'srcset="../../../wp-content/uploads/2024/03/pic-300x150.png 300w, '
            '../../../wp-content/uploads/2024/03/pic.png 1200w"',
            html,
        )
        self.assertIn('sizes="(max-width: 1200px) 100vw, 1200px"', html)
        self.assertIn('>AI &amp; the enterprise<', html)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_blog_related_lib -v`
Expected: `ImportError: cannot import name 'build_card_html'`

- [ ] **Step 3: Implement `build_card_html` in `blog_related_lib.py`**

Add to `blog_related_lib.py`:

```python
def _prefix_url(url: str, prefix: str) -> str:
    return prefix + url.lstrip("/")


def _prefix_srcset(srcset: str, prefix: str) -> str:
    entries = []
    for entry in srcset.split(", "):
        path, width_token = entry.rsplit(" ", 1)
        entries.append(f"{_prefix_url(path, prefix)} {width_token}")
    return ", ".join(entries)


def build_card_html(post: dict, prefix: str) -> str:
    post_href = _prefix_url(post["url"], prefix)
    img_src = _prefix_url(post["image"], prefix)
    blog_href = prefix + "blog/index.html"

    extra_img_attrs = ""
    if post.get("srcset"):
        srcset_val = _prefix_srcset(post["srcset"], prefix)
        extra_img_attrs = (
            f'\n                                srcset="{srcset_val}"'
            f'\n                                sizes="(max-width: {post["width"]}px) 100vw, {post["width"]}px"'
        )

    return f'''                <div
                  data-elementor-type="loop-item"
                  data-elementor-id="31654"
                  class="elementor elementor-31654 e-loop-item e-loop-item-{post['id']} post-{post['id']} insights type-insights status-publish format-standard has-post-thumbnail hentry insights-type-blog"
                  data-elementor-post-type="elementor_library"
                  data-custom-edit-handle="1"
                >
                  <div
                    class="elementor-element elementor-element-393ea075 e-con-full e-flex e-con e-parent"
                    data-id="393ea075"
                    data-element_type="container"
                    data-e-type="container"
                    data-settings='{{"background_background":"classic"}}'
                  >
                    <div
                      class="elementor-element elementor-element-2f1ecd58 e-con-full e-flex e-con e-child"
                      data-id="2f1ecd58"
                      data-element_type="container"
                      data-e-type="container"
                      data-settings='{{"background_background":"classic"}}'
                    >
                      <div
                        class="elementor-element elementor-element-30810b99 e-con-full e-flex e-con e-child"
                        data-id="30810b99"
                        data-element_type="container"
                        data-e-type="container"
                        data-settings='{{"background_background":"classic"}}'
                      >
                        <div
                          class="elementor-element elementor-element-68057356 type-title elementor-widget elementor-widget-post-info"
                          data-id="68057356"
                          data-element_type="widget"
                          data-e-type="widget"
                          data-widget_type="post-info.default"
                        >
                          <ul
                            class="elementor-inline-items elementor-icon-list-items elementor-post-info"
                          >
                            <li
                              class="elementor-icon-list-item elementor-repeater-item-7166291 elementor-inline-item"
                              itemprop="about"
                            >
                              <span
                                class="elementor-icon-list-text elementor-post-info__item elementor-post-info__item--type-terms"
                              >
                                <span class="elementor-post-info__terms-list">
                                  <a
                                    href="{blog_href}"
                                    class="elementor-post-info__terms-list-item"
                                    data-wpel-link="internal"
                                    >Blog</a
                                  >
                                </span>
                              </span>
                            </li>
                          </ul>
                        </div>
                        <div
                          class="elementor-element elementor-element-73d44d2c rltcase elementor-widget elementor-widget-heading"
                          data-id="73d44d2c"
                          data-element_type="widget"
                          data-e-type="widget"
                          data-widget_type="heading.default"
                        >
                          <h4
                            class="elementor-heading-title elementor-size-default"
                          >
                            <a
                              href="{post_href}"
                              data-wpel-link="internal"
                              >{post['title']}</a
                            >
                          </h4>
                        </div>
                      </div>
                      <div
                        class="elementor-element elementor-element-54bf3100 e-flex e-con-boxed e-con e-child"
                        data-id="54bf3100"
                        data-element_type="container"
                        data-e-type="container"
                        data-settings='{{"background_background":"classic"}}'
                      >
                        <div class="e-con-inner">
                          <div
                            class="elementor-element elementor-element-5ee84178 elementor-widget elementor-widget-theme-post-featured-image elementor-widget-image"
                            data-id="5ee84178"
                            data-element_type="widget"
                            data-e-type="widget"
                            data-widget_type="theme-post-featured-image.default"
                          >
                            <a
                              href="{post_href}"
                              data-wpel-link="internal"
                            >
                              <img
                                loading="lazy"
                                width="{post['width']}"
                                height="{post['height']}"
                                src="{img_src}"
                                class="elementor-animation-grow attachment-full size-full wp-image-{post['id']}"
                                alt=""{extra_img_attrs}
                              />
                            </a>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>'''
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_blog_related_lib -v`
Expected: `OK` with 15 tests run, 0 failures.

- [ ] **Step 5: Commit**

```bash
git add blog_related_lib.py tests/test_blog_related_lib.py
git commit -m "feat(blog): add related-post card HTML generation"
```

---

### Task 4: Section replacement (heading + 3 cards)

**Files:**
- Modify: `blog_related_lib.py`
- Test: `tests/test_blog_related_lib.py`

**Interfaces:**
- Consumes: `cards_html: str` — expected to be 3 card blocks (as produced by Task 3's `build_card_html`, one per line-joined with `\n`).
- Produces: `replace_related_section(html_text: str, cards_html: str) -> str`. Raises `ValueError` if the page has no "Other articles that might interest you" heading, or fewer than 3 `data-elementor-type="loop-item"` blocks.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_blog_related_lib.py` (update import line):

```python
from blog_related_lib import (
    clean_title,
    extract_post_data,
    find_srcset,
    build_card_html,
    replace_related_section,
)
```

```python
FIXTURE_PAGE = '''<!doctype html>
<html><body>
<div class="page-content">Article body here.</div>
<div class="elementor-element elementor-element-541f7e1 e-con">
  <div class="e-con-inner">
    <div class="heading-wrap">
      <h3 class="elementor-heading-title elementor-size-default">
        Other articles that might interest you
      </h3>
    </div>
    <div class="elementor-element elementor-element-4d017d1 elementor-widget-loop-grid">
      <div class="elementor-widget-container">
        <div class="elementor-loop-container elementor-grid" role="list">
          <style id="loop-31654">.elementor-31654 { color: red; }</style>
          <div data-elementor-type="loop-item" data-elementor-id="31654" class="old-card-1">
            <div class="inner-1">News card one</div>
          </div>
          <div data-elementor-type="loop-item" data-elementor-id="31654" class="old-card-2">
            <div class="inner-2">Event card two</div>
          </div>
          <div data-elementor-type="loop-item" data-elementor-id="31654" class="old-card-3">
            <div class="inner-3">Event card three</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
</body></html>'''


class ReplaceRelatedSectionTests(unittest.TestCase):
    def test_replaces_heading_text(self):
        result = replace_related_section(FIXTURE_PAGE, "NEW_CARDS_PLACEHOLDER")
        self.assertNotIn("Other articles that might interest you", result)
        self.assertIn("Related blogs", result)

    def test_replaces_all_three_old_cards_with_new_ones(self):
        result = replace_related_section(FIXTURE_PAGE, "NEW_CARDS_PLACEHOLDER")
        self.assertNotIn("old-card-1", result)
        self.assertNotIn("old-card-2", result)
        self.assertNotIn("old-card-3", result)
        self.assertNotIn("News card one", result)
        self.assertEqual(result.count("NEW_CARDS_PLACEHOLDER"), 1)

    def test_preserves_style_block_and_surrounding_structure(self):
        result = replace_related_section(FIXTURE_PAGE, "NEW_CARDS_PLACEHOLDER")
        self.assertIn('<style id="loop-31654">.elementor-31654 { color: red; }</style>', result)
        self.assertIn('<div class="page-content">Article body here.</div>', result)
        self.assertIn('<div class="elementor-widget-container">', result)

    def test_raises_when_heading_missing(self):
        with self.assertRaises(ValueError):
            replace_related_section("<html><body>no heading here</body></html>", "X")

    def test_raises_when_fewer_than_three_cards(self):
        broken = FIXTURE_PAGE.replace(
            '<div data-elementor-type="loop-item" data-elementor-id="31654" class="old-card-3">\n'
            '            <div class="inner-3">Event card three</div>\n'
            '          </div>\n',
            '',
        )
        with self.assertRaises(ValueError):
            replace_related_section(broken, "X")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_blog_related_lib -v`
Expected: `ImportError: cannot import name 'replace_related_section'`

- [ ] **Step 3: Implement `replace_related_section` in `blog_related_lib.py`**

Add to `blog_related_lib.py`:

```python
HEADING_TEXT = "Other articles that might interest you"
NEW_HEADING_TEXT = "Related blogs"
LOOP_ITEM_MARKER = 'data-elementor-type="loop-item"'


def _find_div_end(content: str, start: int) -> int:
    depth, i, n = 0, start, len(content)
    while i < n:
        if content.startswith("<div", i):
            depth += 1
            j = content.find(">", i)
            i = (j + 1) if j != -1 else n
        elif content.startswith("</div>", i):
            depth -= 1
            i += 6
            if depth == 0:
                return i
        else:
            i += 1
    return n


def replace_related_section(html_text: str, cards_html: str) -> str:
    if HEADING_TEXT not in html_text:
        raise ValueError(f"heading '{HEADING_TEXT}' not found")

    updated = html_text.replace(HEADING_TEXT, NEW_HEADING_TEXT, 1)

    search_from = 0
    first_start = None
    end = 0
    for i in range(3):
        marker_idx = updated.find(LOOP_ITEM_MARKER, search_from)
        if marker_idx == -1:
            raise ValueError(f"expected 3 loop-item cards, found {i}")
        item_start = updated.rfind("<div", 0, marker_idx)
        if first_start is None:
            first_start = item_start
        end = _find_div_end(updated, item_start)
        search_from = end

    return updated[:first_start] + cards_html + updated[end:]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_blog_related_lib -v`
Expected: `OK` with 20 tests run, 0 failures.

- [ ] **Step 5: Commit**

```bash
git add blog_related_lib.py tests/test_blog_related_lib.py
git commit -m "feat(blog): add related-articles section replacement logic"
```

---

### Task 5: Driver script

**Files:**
- Create: `update_blog_related.py`

**Interfaces:**
- Consumes: `extract_post_data`, `find_srcset`, `build_card_html`, `replace_related_section` from `blog_related_lib.py` (Tasks 1-4).
- Produces: `data/all-blog-posts.json` (list of post dicts with `id`, `title`, `image`, `width`, `height`, `url`, `srcset`); rewrites the 180 target HTML files in place.

- [ ] **Step 1: Write `update_blog_related.py`**

```python
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
```

- [ ] **Step 2: Verify the target file count matches expectations**

Run: `python -c "from update_blog_related import target_files; print(len(target_files()))"`
Expected: `180`

- [ ] **Step 3: Commit**

```bash
git add update_blog_related.py
git commit -m "feat(blog): add driver script for related-blogs conversion"
```

---

### Task 6: Run the conversion, verify, document, and finalize

**Files:**
- Modify: all 180 files under `blog/*/*/index.html` (excluding `blog/page/*`)
- Create: `data/all-blog-posts.json`
- Modify: `CLAUDE.md` (add script to the automation table)

- [ ] **Step 1: Run the driver script**

Run: `python update_blog_related.py`
Expected output ends with: `Scanned 180 pages, extracted 180 posts, skipped 0` and `Updated 180 of 180 pages` (if any pages are skipped, investigate why before proceeding — do not continue with partial results).

- [ ] **Step 2: Verify no page still has the old heading text**

Run: `grep -rl "Other articles that might interest you" blog --include="index.html" | wc -l`
Expected: `0`

- [ ] **Step 3: Verify every page's own post is excluded from its own cards**

```bash
python - <<'EOF'
from pathlib import Path

ROOT = Path(".")
BLOG = ROOT / "blog"
violations = []
for path in sorted(BLOG.glob("*/*/index.html")):
    if path.parent.parent.name == "page":
        continue
    text = path.read_text(encoding="utf-8")
    own_url = path.relative_to(ROOT).as_posix()
    heading_idx = text.find("Related blogs")
    if heading_idx == -1:
        violations.append((path, "no Related blogs heading"))
        continue
    section = text[heading_idx:]
    if f'href="../../../{own_url}"' in section:
        violations.append((path, "self-referencing card"))

print(f"Checked, violations: {len(violations)}")
for p, reason in violations:
    print(" ", p, reason)
EOF
```

Expected: `Checked, violations: 0`

- [ ] **Step 4: Spot-check visually in the browser**

Run: `python server.py 5502` (in background/separate terminal)

Open `http://127.0.0.1:5502/blog/agility/building-relationship-ai/index.html` and confirm:
- The section heading now reads "Related blogs"
- 3 cards are shown, each badged "Blog", none of them titled "How to build a relationship with an AI" (this page's own title)
- Card layout/spacing matches the homepage's "Related blogs" section

- [ ] **Step 5: Add the new script to CLAUDE.md's automation table**

In `CLAUDE.md`, find the `## Key Automation Scripts` table and add a row:

```markdown
| `update_blog_related.py` | Rebuild `data/all-blog-posts.json` and refresh the "Related blogs" cards on every blog post page |
```

- [ ] **Step 6: Commit the generated content and doc update**

```bash
git add blog data/all-blog-posts.json CLAUDE.md
git commit -m "feat(blog): convert related-articles sections to randomized blog cards

Replaces the hardcoded News/Event cards on all 180 blog post pages with
3 randomly-selected blog posts (excluding the page's own post), matching
the homepage's Related blogs component."
```

- [ ] **Step 7: Final verification**

Run: `python -m unittest tests.test_blog_related_lib -v`
Expected: `OK` (all tests still pass — confirms no regressions from the live run).

Run: `git status`
Expected: working tree clean (everything committed).

---

## Self-Review Notes

- **Spec coverage:** data source/scan (Task 1 + 5), srcset (Task 2), selection & exclusion (Task 5 + 6 Step 3), heading rename (Task 4 + 6 Step 2), card structure/`insights-type-blog` (Task 3), scope limited to 180 pages (Task 5 `target_files`), idempotent re-runs (Task 5's `main()` always rebuilds from scratch, no accumulated state), verification steps (Task 6) — all covered.
- **Type consistency:** `extract_post_data` returns `id/title/image/width/height`; the driver adds `url/srcset` before passing the merged dict into `build_card_html`, which reads exactly those seven keys — consistent across Tasks 1, 2, 3, 5.
