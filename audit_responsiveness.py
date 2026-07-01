#!/usr/bin/env python3
"""
Responsiveness audit for K Techara static site.

Spins up the local server on port 5501, visits every index.html at four
viewport widths, checks for common responsiveness problems, and writes
audit_report.json to the project root.

Usage:
    pip install playwright
    playwright install chromium
    python audit_responsiveness.py
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

# ── Config ────────────────────────────────────────────────────────────────────

SITE_ROOT = Path(__file__).parent.resolve()
SERVER_PORT = 5501
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
OUTPUT_FILE = SITE_ROOT / "audit_report.json"

VIEWPORTS = [
    {"label": "375",  "width": 375,  "height": 812},
    {"label": "768",  "width": 768,  "height": 1024},
    {"label": "1024", "width": 1024, "height": 768},
    {"label": "1440", "width": 1440, "height": 900},
]

CONCURRENCY = 4       # parallel browser contexts
NAV_TIMEOUT = 20_000  # ms per page navigation

# ── JavaScript injected into each page ────────────────────────────────────────

AUDIT_JS = """
(() => {
    const vw = window.innerWidth;
    const issues = {};

    // 1. Horizontal overflow
    issues.horizontal_overflow =
        document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;

    // 2. Viewport meta tag
    const vm = document.querySelector('meta[name="viewport"]');
    issues.missing_viewport_meta = !vm;
    issues.viewport_meta_content = vm ? vm.getAttribute('content') : null;

    // 3. Elements wider than the viewport
    const SELECTOR = [
        'section',
        '.e-con',
        '.elementor-section',
        '.elementor-container',
        '.elementor-widget-wrap',
        '.elementor-row',
        'div[class*="elementor-"]',
        'header',
        'footer',
        'nav',
    ].join(', ');

    const wideEls = [];
    const seen = new Set();
    for (const el of document.querySelectorAll(SELECTOR)) {
        try {
            const r = el.getBoundingClientRect();
            if (r.width > vw + 2) {
                const key = el.tagName + '|' + el.className;
                if (seen.has(key)) continue;
                seen.add(key);
                const inlineStyle = (el.getAttribute('style') || '').substring(0, 200);
                // capture fixed --width custom property if present
                const widthMatch = inlineStyle.match(/--width\\s*:\\s*([^;]+)/);
                wideEls.push({
                    tag: el.tagName.toLowerCase(),
                    classes: Array.from(el.classList).slice(0, 8).join(' '),
                    id: el.id || null,
                    width_px: Math.round(r.width),
                    inline_width_var: widthMatch ? widthMatch[1].trim() : null,
                    inline_style_snippet: inlineStyle,
                });
                if (wideEls.length >= 15) break;
            }
        } catch (e) {}
    }
    issues.fixed_width_elements = wideEls;

    // 4. Images actually rendered wider than the viewport
    const badImgs = [];
    for (const img of document.querySelectorAll('img')) {
        try {
            const r = img.getBoundingClientRect();
            // Only flag images that are truly overflowing the viewport — skip
            // zero-width (hidden) images and images that fit within the viewport.
            if (r.width > vw + 2 && r.width > 0) {
                const cs = getComputedStyle(img);
                badImgs.push({
                    src: (img.getAttribute('src') || '').split('/').slice(-1)[0],
                    rendered_width_px: Math.round(r.width),
                    has_width_attr: img.hasAttribute('width'),
                    width_attr_value: img.getAttribute('width'),
                    max_width_computed: cs.maxWidth,
                    wider_than_viewport: true,
                });
                if (badImgs.length >= 8) break;
            }
        } catch (e) {}
    }
    issues.images_without_max_width = badImgs;

    // 5. Media queries present somewhere on this page
    let hasMediaQ = false;
    for (const s of document.querySelectorAll('style')) {
        if (s.textContent.includes('@media')) { hasMediaQ = true; break; }
    }
    // also try accessible cross-origin sheets (same-origin since local server)
    if (!hasMediaQ) {
        try {
            for (const sheet of document.styleSheets) {
                try {
                    for (const rule of sheet.cssRules || []) {
                        if (rule.type === CSSRule.MEDIA_RULE) {
                            hasMediaQ = true;
                            break;
                        }
                    }
                } catch (e) {}
                if (hasMediaQ) break;
            }
        } catch (e) {}
    }
    issues.no_media_queries = !hasMediaQ;

    // 6. Elements that overflow their parent (clipped/overlapping)
    const overflowingEls = [];
    for (const el of document.querySelectorAll(SELECTOR)) {
        try {
            const parent = el.parentElement;
            if (!parent) continue;
            const elR = el.getBoundingClientRect();
            const parR = parent.getBoundingClientRect();
            const overflow = Math.round(elR.right - parR.right);
            if (overflow > 4) {
                // Skip elements clipped by a parent with overflow:hidden/clip —
                // the overflow is invisible to users (e.g. Elementor parallax layers).
                const parentOvf = getComputedStyle(parent).overflow;
                const parentOvfX = getComputedStyle(parent).overflowX;
                const isClipped = parentOvf === 'hidden' || parentOvf === 'clip'
                               || parentOvfX === 'hidden' || parentOvfX === 'clip';
                if (isClipped) continue;
                overflowingEls.push({
                    tag: el.tagName.toLowerCase(),
                    classes: Array.from(el.classList).slice(0, 6).join(' '),
                    overflow_right_px: overflow,
                });
                if (overflowingEls.length >= 8) break;
            }
        } catch (e) {}
    }
    issues.overflowing_elements = overflowingEls;

    return issues;
})()
"""

# ── Page discovery ─────────────────────────────────────────────────────────────

def discover_pages():
    """Return list of (relative_path_str, url) for every index.html, excluding wp-content."""
    pages = []
    for html_file in sorted(SITE_ROOT.rglob("index.html")):
        rel = html_file.relative_to(SITE_ROOT)
        parts = rel.parts
        # skip anything inside wp-content or hidden dirs
        if any(p.startswith(".") or p == "wp-content" or p == "__pycache__" for p in parts):
            continue
        # convert path to URL: "blog/foo/index.html" → "/blog/foo/"
        url_path = "/" + "/".join(parts[:-1]) + ("/" if len(parts) > 1 else "")
        url = BASE_URL + url_path
        pages.append((str(rel).replace("\\", "/"), url))
    return pages


# ── Per-page audit ─────────────────────────────────────────────────────────────

async def audit_page(browser, rel_path, url, sem, idx, total):
    viewport_results = {}
    error = None

    try:
        async with sem:
            for vp in VIEWPORTS:
                context = await browser.new_context(
                    viewport={"width": vp["width"], "height": vp["height"]},
                    ignore_https_errors=True,
                )
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
                    # brief pause for any deferred CSS to apply
                    await page.wait_for_timeout(300)
                    issues = await page.evaluate(AUDIT_JS)
                    has_issues = (
                        issues.get("horizontal_overflow")
                        or issues.get("missing_viewport_meta")
                        or issues.get("no_media_queries")
                        or bool(issues.get("fixed_width_elements"))
                        or bool(issues.get("images_without_max_width"))
                        or bool(issues.get("overflowing_elements"))
                    )
                    viewport_results[vp["label"]] = {
                        "passed": not has_issues,
                        "issues": issues,
                    }
                except Exception as e:
                    viewport_results[vp["label"]] = {
                        "passed": False,
                        "issues": {},
                        "nav_error": str(e)[:200],
                    }
                finally:
                    await context.close()
    except Exception as e:
        error = str(e)[:300]

    label = f"[{idx+1}/{total}]"
    status = "ERR" if error else ("FAIL" if any(not v["passed"] for v in viewport_results.values()) else "OK ")
    print(f"  {label} {status}  {rel_path}", flush=True)

    return {
        "relative_path": rel_path,
        "url": url,
        "viewports": viewport_results,
        "error": error,
    }


# ── Server management ──────────────────────────────────────────────────────────

def start_server():
    proc = subprocess.Popen(
        [sys.executable, str(SITE_ROOT / "server.py"), str(SERVER_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(SITE_ROOT),
    )
    time.sleep(1.5)  # give it a moment to bind
    return proc


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    print("K Techara — Responsiveness Audit")
    print("=" * 50)

    # Discover pages
    pages = discover_pages()
    print(f"Found {len(pages)} pages to audit")

    # Start server
    print(f"Starting local server on port {SERVER_PORT}...")
    server_proc = start_server()

    results = []
    started_at = datetime.now(timezone.utc)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            sem = asyncio.Semaphore(CONCURRENCY)
            total = len(pages)
            print(f"Auditing {total} pages at {len(VIEWPORTS)} viewports each "
                  f"({CONCURRENCY} concurrent)...\n")
            tasks = [
                audit_page(browser, rel, url, sem, idx, total)
                for idx, (rel, url) in enumerate(pages)
            ]
            results = await asyncio.gather(*tasks)
            await browser.close()
    finally:
        server_proc.terminate()

    # Summarise
    total_pages = len(results)
    failing_pages = sum(
        1 for r in results
        if r["error"] or any(not v["passed"] for v in r["viewports"].values())
    )
    error_pages = sum(1 for r in results if r["error"])

    print(f"\n{'='*50}")
    print(f"Audit complete: {total_pages} pages, {failing_pages} with issues, {error_pages} errors")

    # Write report
    report = {
        "generated_at": started_at.isoformat(),
        "site_root": BASE_URL,
        "total_pages": total_pages,
        "failing_pages": failing_pages,
        "error_pages": error_pages,
        "viewports_tested": [vp["label"] for vp in VIEWPORTS],
        "pages": results,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Report written to: {OUTPUT_FILE}")
    print(f"Next step: python triage_report.py")


if __name__ == "__main__":
    asyncio.run(main())