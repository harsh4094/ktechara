# K Techara — Project Context

## Site Overview

Static HTML website (407 pages) exported from WordPress/Elementor.
Production host: Apache on Hostinger (`www.techara.co.uk`).
No active PHP/WordPress — all pages are pre-rendered HTML served as static files.

## Folder Structure

```
ktechara/
├── index.html                  ← Homepage
├── 404/                        ← Custom error page
├── about-us/                   ← Company info + sub-pages
│   ├── case-studies/
│   ├── financing/
│   ├── frameworks/
│   ├── leadership/
│   ├── people-culture-and-careers/
│   └── sustainability-and-social-value/
├── blog/                       ← Blog posts (13 category subdirs)
│   ├── agility/, ai-and-automation/, azure-and-cloud/,
│   │   compliance/, data/, efficiency/, employee-experience/,
│   │   future-readiness/, infrastructure/, modern-work/,
│   │   security/, strategy/, sustainability/
│   └── page/                   ← Pagination
├── contact-us/
├── events/                     ← 4 category subdirs
├── insights/
├── leadership/                 ← 17 individual bio pages
├── our-services/
├── our-solutions/
├── partners/
├── podcast/
├── solutions-by-sector/
└── wp-content/                 ← All assets (do not touch HTML here)
    ├── plugins/                ← Elementor, Premium Addons, Search Filter
    ├── themes/hello-elementor/ ← Base theme CSS
    └── uploads/
        ├── elementor/css/      ← Per-page generated CSS (post-*.css)
        └── [year]/             ← Images organised by upload year
```

Each page is an `index.html` in its own directory (directory-based routing).

## Template System

Header and footer are **baked into every HTML file** via:

```bash
python build_header_footer.py
```

Source templates:
- `_header.html` — Elementor nav/mega-menu markup
- `_footer.html` — Elementor footer markup

Editing `_header.html` or `_footer.html` then running `build_header_footer.py`
propagates the change to all 407 pages simultaneously. Any responsiveness bug
in the header or footer is therefore a **single root cause affecting every page**.

## CSS Architecture

Pages load CSS in this order:

1. **Inline `<style>` blocks** — WordPress/Elementor global variables, auto-sizes,
   SVG icon rules, `global-styles-inline-css` (500–2000 lines of CSS custom properties
   including font sizes, spacing, colour palette).
2. **Typekit fonts** — `wp-content/themes/hello-theme-child-master/fonts/typekit.css`
3. **Elementor core CSS** — `wp-content/plugins/elementor/assets/css/frontend*.css`
4. **Elementor Pro / Premium Addons CSS** — plugin stylesheets
5. **Hello Elementor theme CSS** — `reset.css`, `theme.css`, `header-footer.css`
6. **Shared template CSS** (Elementor post CSS files, linked via `<link>` tags):
   - `post-7.css` — **Header template** — present on *every* page
   - `post-31649.css`, `post-33272.css`, `post-29220.css` — shared section/widget templates
   - `post-29147.css`, `post-31632.css`, `post-28392.css` — **Footer template** (at end of page)
7. **Per-page CSS** — unique `post-XXXXX.css` for each page's Elementor layout

**Key responsive facts:**
- Breakpoints in theme/plugin CSS: 480, 576, 768, 992, 1024, 1366, 2400px
- Elementor uses inline CSS custom properties for sizing: `style="--width:241px; --padding-top:0px"`
  These do not inherently shrink with the viewport.
- Some images carry HTML dimension attributes (`width="377" height="308"`) without a
  CSS `max-width: 100%` override, causing overflow at small viewports.
- All pages have correct viewport meta: `<meta name="viewport" content="width=device-width, initial-scale=1" />`

## Local Dev Server

```bash
python server.py          # serves http://127.0.0.1:5500/
python server.py 5501     # alternate port (used by audit script)
```

Python `SimpleHTTPServer` wrapper with custom 404 handling. No build step needed.

## Key Automation Scripts

| Script | Purpose |
|--------|---------|
| `build_header_footer.py` | Inject `_header.html` + `_footer.html` into all pages |
| `server.py` | Local static file server (port 5500) |
| `fix_paths.py` | Fix relative/absolute asset paths |
| `clean_nav.py` | Navigation cleanup |
| `update_related_blogs.py` | Auto-update blog cross-links |
| `download_typekit_fonts.py` | Download Adobe fonts locally |
| `replace_advania.py` | Replace old Advania domain references |

## Responsiveness Audit Artifacts

After running the audit:
- `audit_report.json` — Raw per-page, per-viewport findings (407 entries)
- `triage_report.json` — Clustered root-cause analysis
- `audit_responsiveness.py` — Playwright script that generated the report
- `triage_report.py` — Clustering/analysis script

Run audit:
```bash
pip install playwright && playwright install chromium
python audit_responsiveness.py   # ~10 min, writes audit_report.json
python triage_report.py          # reads JSON, writes triage_report.json + prints summary
```

## Git

Branch: `dev`. Main branch: `main`. Do not commit audit artifacts (JSON files).