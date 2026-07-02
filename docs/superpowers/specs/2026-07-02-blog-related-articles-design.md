# Convert "Other articles that might interest you" to "Related blogs" on all blog post pages

## Problem

Every one of the 180 individual blog post pages (`blog/<category>/<slug>/index.html`) ends
with an "Other articles that might interest you" section. Its 3 cards are hardcoded and
identical across every page: 1 News item and 2 Event items. They are never related to the
post being read, and the "News"/"Event" content doesn't belong on a blog post.

The homepage (`index.html`) already has a "Related blogs" section using the same underlying
Elementor loop-grid template (`template_id: 31654`), just populated with blog posts labelled
"Blog" instead of News/Events. This is the target shape.

## Scope

- **In scope:** the 180 pages matching `blog/*/*/index.html` (excludes `blog/page/*`
  pagination pages).
- **Out of scope:** podcast pages (23) and the stray `mysql-sql-injection-practical-cheat-sheet`
  page, which currently share the same component but are not part of this change.
- `data/blog-posts.json` (3-entry file used by the homepage and `our-solutions` pages via
  `update_related_blogs.py`) is untouched.

## Data source

A new script scans all 180 blog post pages and builds a database of every post:

- `title` — from `<title>`, with trailing ` - K Techara`, ` – K Techara`, ` - K Techara UK`
  style suffixes stripped (regex-based, must handle multi-line `<title>` tags).
- `url` — the post's own path, relative to the project root, forward-slash form
  (e.g. `blog/agility/building-relationship-ai/index.html`).
- `image`, `width`, `height` — from `og:image`, `og:image:width`, `og:image:height` meta
  tags (all 180 pages have `og:image`; width/height fall back to `1200`x`600` if absent).
- `srcset` — built by checking disk for sibling resized files next to the `og:image` file
  matching the WordPress `-{width}x{height}.{ext}` naming convention (e.g. `-300x200.jpg`,
  `-768x512.jpg`, `-1024x683.jpg`, `-1536x1025.jpg`), sorted ascending by width. Posts with
  no such siblings (85 of 180) get a plain `src` with no `srcset` attribute.

This database is saved to `data/all-blog-posts.json` (new file, separate from the existing
`data/blog-posts.json`).

## Selection & replacement logic

For each of the 180 pages, the script:

1. Identifies the post's own record in the database (by matching its file path) so it can
   be excluded from its own related list.
2. Picks 3 random posts from the database excluding itself, via `random.sample()`. No fixed
   seed — re-running the script produces a fresh shuffle on every page, every run.
3. Replaces the heading text "Other articles that might interest you" with "Related blogs",
   matching the homepage's wording for the same component.
4. Replaces the 3 hardcoded `<div data-elementor-type="loop-item" ...>...</div>` card blocks
   inside the `elementor-loop-container` with 3 newly generated cards for the chosen posts.
   The `<style id="loop-31654">` block and all surrounding structure/CSS are left untouched
   — only the 3 card divs change.
5. Each generated card:
   - Badge reads "Blog", linking to `blog/index.html` (relative to the page's depth, which
     is always `../../../` for these 3-levels-deep pages).
   - Heading links to the chosen post's URL.
   - Image uses the chosen post's `src`/`srcset`/`width`/`height`, all paths made relative
     to the current page.
   - Card wrapper class uses `insights-type-blog` (matching the homepage's own cards) instead
     of the current `insights-type-news` / `insights-type-events`. This class isn't read by
     any CSS or JS on the site — it's inert WordPress-export metadata — so the change is
     cosmetic/consistency-only.

## Idempotency

The script can be re-run at any time to reshuffle all 180 pages' related-post picks; it always
regenerates from the current database rather than depending on the previous output, so re-runs
are safe and don't compound.

## Verification

After running:
- Confirm all 180 target pages have the heading "Related blogs" and no page still contains
  "Other articles that might interest you".
- Confirm no page's 3 related cards include a link back to that same page's own URL.
- Spot-check a handful of pages in the local dev server (`python server.py`) to confirm layout
  matches the homepage's "Related blogs" section visually.
