#!/usr/bin/env python3
"""
Triage and cluster the findings from audit_report.json.

Reads audit_report.json (produced by audit_responsiveness.py), cross-references
each failing page's linked Elementor CSS files, and groups pages by shared root
cause. Outputs triage_report.json and prints a ranked human-readable summary.

Usage:
    python triage_report.py
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SITE_ROOT = Path(__file__).parent.resolve()
AUDIT_FILE = SITE_ROOT / "audit_report.json"
OUTPUT_FILE = SITE_ROOT / "triage_report.json"

# Known shared Elementor template CSS post IDs (discovered during exploration)
KNOWN_TEMPLATES = {
    "7":     "Header template (all pages)",
    "29147": "Footer template (most pages)",
    "31632": "Footer template (most pages)",
    "28392": "Footer template (most pages)",
    "31649": "Shared section/widget template",
    "33272": "Shared section/widget template",
    "29220": "Shared section/widget template",
}

VIEWPORTS = ["375", "768", "1024", "1440"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_audit():
    with open(AUDIT_FILE, encoding="utf-8") as f:
        return json.load(f)


def extract_post_ids(html_path: Path) -> set:
    """Parse an HTML file and return the set of Elementor post-*.css IDs it links."""
    try:
        text = html_path.read_text(encoding="utf-8", errors="ignore")
        return set(re.findall(r'post-(\d+)\.css', text))
    except OSError:
        return set()


def page_has_any_failure(page_data):
    if page_data.get("error"):
        return True
    return any(not vp.get("passed", True) for vp in page_data["viewports"].values())


def first_failing_viewport(page_data):
    for vp in VIEWPORTS:
        vp_data = page_data["viewports"].get(vp, {})
        if not vp_data.get("passed", True) or vp_data.get("nav_error"):
            return vp
    return None


# ── Clustering ────────────────────────────────────────────────────────────────

def build_clusters(audit):
    failing_pages = [p for p in audit["pages"] if page_has_any_failure(p)]

    # ── 1. Build page → post_ids map ──────────────────────────────────────────
    page_post_ids = {}
    for page in failing_pages:
        html_path = SITE_ROOT / page["relative_path"]
        page_post_ids[page["relative_path"]] = extract_post_ids(html_path)

    # ── 2. Shared-CSS clusters ────────────────────────────────────────────────
    post_to_pages = defaultdict(list)
    for page in failing_pages:
        for pid in page_post_ids.get(page["relative_path"], set()):
            post_to_pages[pid].append(page["relative_path"])

    # ── 3. Element class frequency across all failing pages ───────────────────
    class_counter = Counter()
    for page in failing_pages:
        for vp_data in page["viewports"].values():
            issues = vp_data.get("issues", {})
            for el in issues.get("fixed_width_elements", []):
                for cls in el.get("classes", "").split():
                    if cls and "elementor" in cls:
                        class_counter[cls] += 1
            for el in issues.get("overflowing_elements", []):
                for cls in el.get("classes", "").split():
                    if cls:
                        class_counter[cls] += 1

    # ── 4. Viewport failure breakdown ─────────────────────────────────────────
    viewport_fail_counts = Counter()
    for page in failing_pages:
        for vp in VIEWPORTS:
            vp_data = page["viewports"].get(vp, {})
            if not vp_data.get("passed", True):
                viewport_fail_counts[vp] += 1

    # ── 5. Issue type breakdown ───────────────────────────────────────────────
    issue_type_counts = Counter()
    for page in failing_pages:
        for vp_data in page["viewports"].values():
            issues = vp_data.get("issues", {})
            if issues.get("horizontal_overflow"):
                issue_type_counts["horizontal_overflow"] += 1
            if issues.get("missing_viewport_meta"):
                issue_type_counts["missing_viewport_meta"] += 1
            if issues.get("no_media_queries"):
                issue_type_counts["no_media_queries"] += 1
            if issues.get("fixed_width_elements"):
                issue_type_counts["fixed_width_elements"] += 1
            if issues.get("images_without_max_width"):
                issue_type_counts["images_without_max_width"] += 1
            if issues.get("overflowing_elements"):
                issue_type_counts["overflowing_elements"] += 1

    # ── 6. Assemble clusters ──────────────────────────────────────────────────
    clusters = []

    # Cluster A: pages that fail at 375px (mobile) — biggest set
    mobile_fail = [p["relative_path"] for p in failing_pages
                   if first_failing_viewport(p) == "375"]
    if mobile_fail:
        # find the most common shared post-CSS among these pages
        shared_counter = Counter()
        for rp in mobile_fail:
            for pid in page_post_ids.get(rp, set()):
                shared_counter[pid] += 1
        top_shared = [pid for pid, _ in shared_counter.most_common(5)]
        clusters.append({
            "cluster_id": "A",
            "root_cause": "Mobile viewport overflow (375px)",
            "description": (
                "Pages that show horizontal scroll or element overflow at 375px. "
                "Most likely caused by fixed-width Elementor containers or sections "
                "that don't collapse at mobile widths."
            ),
            "pages_affected": len(mobile_fail),
            "first_failing_viewport": "375",
            "top_shared_css_post_ids": top_shared,
            "top_shared_templates": {pid: KNOWN_TEMPLATES.get(pid, "Page-specific") for pid in top_shared[:3]},
            "representative_pages": mobile_fail[:5],
            "proposed_fix": (
                "In the shared header template (_header.html / post-7.css): add "
                "`max-width: 100%; overflow-x: hidden;` to the outermost nav container. "
                "For body sections: audit any inline `--width:Xpx` custom properties on "
                "`.e-con` and `.elementor-section` elements and convert to "
                "`max-width: Xpx; width: 100%;`."
            ),
        })

    # Cluster B: pages failing at 768 but not 375 (tablet-only issues)
    tablet_only = [p["relative_path"] for p in failing_pages
                   if first_failing_viewport(p) == "768"]
    if tablet_only:
        clusters.append({
            "cluster_id": "B",
            "root_cause": "Tablet viewport overflow (768px) — passes mobile",
            "description": (
                "Pages that pass at 375px but overflow at 768px. "
                "Likely caused by elements that are hidden/collapsed on mobile but "
                "appear at tablet width with a fixed pixel dimension."
            ),
            "pages_affected": len(tablet_only),
            "first_failing_viewport": "768",
            "representative_pages": tablet_only[:5],
            "proposed_fix": (
                "Check elements that are conditionally shown at tablet breakpoints "
                "(e.g., Elementor's `elementor-hidden-mobile` elements). "
                "Add `max-width: 100%; width: 100%;` to these elements in the "
                "shared section CSS files."
            ),
        })

    # Cluster C: fixed-width element class clusters
    top_classes = class_counter.most_common(10)
    if top_classes:
        clusters.append({
            "cluster_id": "C",
            "root_cause": "Fixed-width Elementor elements (by CSS class)",
            "description": "The most frequently overflowing Elementor element classes across all failing pages.",
            "top_offending_classes": [
                {"class": cls, "occurrences": count}
                for cls, count in top_classes
            ],
            "pages_affected": len(failing_pages),
            "proposed_fix": (
                "For each class in the top list: add `max-width: 100%; overflow: hidden;` "
                "in the shared CSS file that defines that class. For Elementor sections "
                "(`elementor-section-full_width`, `e-con-full`): ensure the container "
                "uses `width: 100%` not a fixed pixel value."
            ),
        })

    # Cluster D: shared header template (post-7) issues
    header_affected = post_to_pages.get("7", [])
    if header_affected:
        clusters.append({
            "cluster_id": "D",
            "root_cause": "Shared header template (post-7.css) — affects all pages",
            "description": (
                f"post-7.css is linked by {len(header_affected)} pages (the entire site). "
                "Any overflow or layout break in this file cascades to every single page."
            ),
            "pages_affected": len(header_affected),
            "shared_css_file": "wp-content/uploads/elementor/css/post-7.css",
            "source_template": "_header.html",
            "representative_pages": header_affected[:3],
            "proposed_fix": (
                "Open `wp-content/uploads/elementor/css/post-7.css` and identify rules "
                "with fixed `width: Xpx` (not max-width). Add responsive overrides. "
                "Then edit `_header.html` and run `build_header_footer.py` to propagate — "
                "this single fix will resolve the header issue on all 407 pages."
            ),
        })

    # Cluster E: shared footer template issues
    footer_ids = ["29147", "31632", "28392"]
    footer_pages = set()
    for fid in footer_ids:
        footer_pages.update(post_to_pages.get(fid, []))
    if footer_pages:
        clusters.append({
            "cluster_id": "E",
            "root_cause": "Shared footer template (post-29147/31632/28392) — affects most pages",
            "description": (
                f"{len(footer_pages)} pages link the shared footer CSS files. "
                "Footer layout issues propagate site-wide."
            ),
            "pages_affected": len(footer_pages),
            "shared_css_files": [f"wp-content/uploads/elementor/css/post-{fid}.css" for fid in footer_ids],
            "source_template": "_footer.html",
            "representative_pages": list(footer_pages)[:3],
            "proposed_fix": (
                "Audit footer CSS files for fixed widths. Edit `_footer.html` and run "
                "`build_header_footer.py` to apply across all pages."
            ),
        })

    # Cluster F: images without max-width
    img_pages = []
    img_counter = Counter()
    for page in failing_pages:
        for vp_data in page["viewports"].values():
            imgs = vp_data.get("issues", {}).get("images_without_max_width", [])
            if imgs:
                img_pages.append(page["relative_path"])
                for img in imgs:
                    img_counter[img.get("src", "unknown")] += 1
                break
    img_pages = list(dict.fromkeys(img_pages))  # deduplicate preserving order
    if img_pages:
        clusters.append({
            "cluster_id": "F",
            "root_cause": "Images without max-width:100% constraint",
            "description": (
                "Images with HTML `width` attributes but no CSS `max-width: 100%` — "
                "they overflow their container at narrow viewports."
            ),
            "pages_affected": len(img_pages),
            "top_offending_images": [
                {"filename": src, "occurrences": count}
                for src, count in img_counter.most_common(10)
            ],
            "representative_pages": img_pages[:5],
            "proposed_fix": (
                "Add `img { max-width: 100%; height: auto; }` to the global stylesheet "
                "(e.g., append to the `global-styles-inline-css` block in _header.html, "
                "or add a site-wide `<style>` in _header.html before other styles)."
            ),
        })

    # Cluster G: pages with no media queries at all
    no_mq_pages = []
    for page in failing_pages:
        for vp_data in page["viewports"].values():
            if vp_data.get("issues", {}).get("no_media_queries"):
                no_mq_pages.append(page["relative_path"])
                break
    no_mq_pages = list(dict.fromkeys(no_mq_pages))
    if no_mq_pages:
        clusters.append({
            "cluster_id": "G",
            "root_cause": "No media queries detected on page",
            "description": (
                "Pages where no `@media` rule was found in any inline style block. "
                "These pages have zero responsive breakpoints of their own — they rely "
                "entirely on linked external CSS files for responsiveness."
            ),
            "pages_affected": len(no_mq_pages),
            "representative_pages": no_mq_pages[:5],
            "proposed_fix": (
                "These pages need breakpoints added. Since they use Elementor, the fix "
                "is in their per-page `post-XXXXX.css` file or via re-exporting from "
                "the Elementor editor with responsive settings enabled."
            ),
        })

    # sort clusters by pages_affected desc
    clusters.sort(key=lambda c: c.get("pages_affected", 0), reverse=True)
    return clusters, viewport_fail_counts, issue_type_counts, failing_pages


# ── Output ────────────────────────────────────────────────────────────────────

def print_summary(audit, clusters, viewport_fail_counts, issue_type_counts, failing_pages):
    total = audit["total_pages"]
    failing = len(failing_pages)
    pct = 100 * failing / total if total else 0

    print("\n" + "=" * 60)
    print("TRIAGE SUMMARY — K Techara Responsiveness Audit")
    print("=" * 60)
    print(f"Total pages:    {total}")
    print(f"Failing pages:  {failing}  ({pct:.1f}%)")
    print(f"Error pages:    {audit.get('error_pages', 0)}")

    print("\nFailing pages by viewport:")
    for vp in ["375", "768", "1024", "1440"]:
        count = viewport_fail_counts.get(vp, 0)
        bar = "#" * (count * 30 // max(failing, 1))
        print(f"  {vp:>4}px  {count:>4} pages  {bar}")

    print("\nIssue type breakdown (viewport-level occurrences):")
    for issue, count in issue_type_counts.most_common():
        print(f"  {issue:<35} {count:>5}")

    print(f"\nRoot-cause clusters ({len(clusters)} found, ranked by pages affected):")
    print("-" * 60)
    for c in clusters:
        pa = c.get("pages_affected", 0)
        print(f"  [{c['cluster_id']}] {c['root_cause']}")
        print(f"       Pages affected: {pa}")
        if "proposed_fix" in c:
            fix_preview = c["proposed_fix"][:120].replace("\n", " ")
            print(f"       Fix preview:  {fix_preview}...")
        print()


def main():
    if not AUDIT_FILE.exists():
        print(f"ERROR: {AUDIT_FILE} not found. Run audit_responsiveness.py first.")
        raise SystemExit(1)

    print(f"Loading {AUDIT_FILE}...")
    audit = load_audit()

    clusters, viewport_fail_counts, issue_type_counts, failing_pages = build_clusters(audit)

    print_summary(audit, clusters, viewport_fail_counts, issue_type_counts, failing_pages)

    report = {
        "generated_at": audit.get("generated_at"),
        "total_pages": audit["total_pages"],
        "failing_pages": len(failing_pages),
        "error_pages": audit.get("error_pages", 0),
        "viewport_failure_counts": dict(viewport_fail_counts),
        "issue_type_counts": dict(issue_type_counts),
        "clusters": clusters,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nTriage report written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()