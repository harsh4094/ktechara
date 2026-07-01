#!/usr/bin/env python3
"""
Validation script for K Techara audit findings.

Step 1: For the 3 pages with actual horizontal scrollbars (our-services, our-solutions,
        solutions-by-sector) — find the actual DOM element causing scrollWidth > clientWidth.

Step 2: For 5 representative pages with elementor-motion-effects-layer overflow — inspect
        whether the parent has overflow:hidden (clipped/invisible) or not (real user impact).

Outputs: per-page findings to stdout + screenshots to /scratchpad/.

Usage: python validate_overflow.py
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

SITE_ROOT = Path(__file__).parent.resolve()
SERVER_PORT = 5502
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
SCREENSHOT_DIR = Path(r"C:\Users\STARKS~1\AppData\Local\Temp\claude\d--TrainingGround-BHAVIK-PROJECTS-ktechara\0ab4a388-b667-470f-a480-c9cf9aba275e\scratchpad\screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# ── Pages ──────────────────────────────────────────────────────────────────────

# Step 1: Pages with actual page-level horizontal scroll
STRICT_OVERFLOW_PAGES = [
    ("our-services/index.html",          "/our-services/"),
    ("our-solutions/index.html",         "/our-solutions/"),
    ("solutions-by-sector/index.html",   "/solutions-by-sector/"),
]

# Step 2: Pages with motion-effects overflow (from 5 different site sections)
MOTION_EFFECTS_PAGES = [
    ("about-us/index.html",                                              "/about-us/"),
    ("blog/agility/building-relationship-ai/index.html",                "/blog/agility/building-relationship-ai/"),
    ("contact-us/index.html",                                            "/contact-us/"),
    ("events/ai-and-automation/ai-briefing-and-lunch-discussion-in-dublin/index.html",
     "/events/ai-and-automation/ai-briefing-and-lunch-discussion-in-dublin/"),
    ("index.html",                                                       "/"),
]

VIEWPORTS = [375, 768, 1024, 1440]

# ── JavaScript ────────────────────────────────────────────────────────────────

FIND_SCROLL_CAUSE_JS = """
(() => {
    const vw = document.documentElement.clientWidth;
    const sw = document.documentElement.scrollWidth;
    if (sw <= vw + 2) return { no_overflow: true, scrollWidth: sw, clientWidth: vw };

    // Walk ALL elements to find what extends past viewport right edge
    const culprits = [];
    for (const el of document.body.querySelectorAll('*')) {
        try {
            const r = el.getBoundingClientRect();
            if (r.right > vw + 2) {
                const cs = getComputedStyle(el);
                const parent = el.parentElement;
                const parentR = parent ? parent.getBoundingClientRect() : null;
                const parentOvf = parent ? getComputedStyle(parent).overflow : null;
                culprits.push({
                    tag: el.tagName.toLowerCase(),
                    id: el.id || null,
                    classes: Array.from(el.classList).join(' ').substring(0, 120),
                    right: Math.round(r.right),
                    width: Math.round(r.width),
                    left: Math.round(r.left),
                    computed_width: cs.width,
                    computed_position: cs.position,
                    computed_overflow: cs.overflow,
                    inline_style: (el.getAttribute('style') || '').substring(0, 150),
                    parent_overflow: parentOvf,
                    parent_right: parentR ? Math.round(parentR.right) : null,
                });
                if (culprits.length >= 5) break;
            }
        } catch (e) {}
    }
    return {
        no_overflow: false,
        scrollWidth: sw,
        clientWidth: vw,
        culprits,
    };
})()
"""

MOTION_EFFECTS_INSPECT_JS = """
(() => {
    const vw = document.documentElement.clientWidth;
    const results = [];
    for (const layer of document.querySelectorAll('.elementor-motion-effects-layer')) {
        const r = layer.getBoundingClientRect();
        const cs = getComputedStyle(layer);
        const parent = layer.parentElement;
        const grandParent = parent ? parent.parentElement : null;
        const parentEl = parent ? parent.getBoundingClientRect() : null;
        const gpEl = grandParent ? grandParent.getBoundingClientRect() : null;
        const parentOvf = parent ? getComputedStyle(parent).overflow + '/' + getComputedStyle(parent).overflowX : null;
        const gpOvf = grandParent ? getComputedStyle(grandParent).overflow + '/' + getComputedStyle(grandParent).overflowX : null;
        results.push({
            layer_left: Math.round(r.left),
            layer_right: Math.round(r.right),
            layer_width: Math.round(r.width),
            layer_width_computed: cs.width,
            layer_position: cs.position,
            layer_transform: cs.transform,
            viewport_width: vw,
            overflow_past_viewport: Math.round(r.right - vw),
            parent_tag: parent ? parent.tagName.toLowerCase() : null,
            parent_classes: parent ? Array.from(parent.classList).join(' ').substring(0, 80) : null,
            parent_overflow: parentOvf,
            parent_right: parentEl ? Math.round(parentEl.right) : null,
            overflow_past_parent: parentEl ? Math.round(r.right - parentEl.right) : null,
            grandparent_overflow: gpOvf,
            grandparent_right: gpEl ? Math.round(gpEl.right) : null,
        });
        if (results.length >= 4) break;
    }
    const pageHasScrollbar = document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
    return { layers: results, page_has_horizontal_scrollbar: pageHasScrollbar };
})()
"""

# ── Server ────────────────────────────────────────────────────────────────────

def start_server():
    proc = subprocess.Popen(
        [sys.executable, str(SITE_ROOT / "server.py"), str(SERVER_PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(SITE_ROOT)
    )
    time.sleep(1.5)
    return proc

# ── Runners ───────────────────────────────────────────────────────────────────

async def step1_strict_overflow(browser):
    print("\n" + "="*70)
    print("STEP 1 — FINDING REAL SCROLLBAR CAUSE (our-services / our-solutions / solutions-by-sector)")
    print("="*70)

    for rel, url_path in STRICT_OVERFLOW_PAGES:
        url = BASE_URL + url_path
        print(f"\n  PAGE: {rel}")
        for vp_w in [375, 768, 1024]:
            ctx = await browser.new_context(
                viewport={"width": vp_w, "height": 900},
                ignore_https_errors=True,
            )
            page = await ctx.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(400)
                result = await page.evaluate(FIND_SCROLL_CAUSE_JS)
                if result.get("no_overflow"):
                    print(f"    [{vp_w}px] No overflow detected (scrollWidth={result['scrollWidth']})")
                    continue
                print(f"    [{vp_w}px] scrollWidth={result['scrollWidth']} clientWidth={result['clientWidth']} — culprits:")
                for c in result.get("culprits", []):
                    print(f"      <{c['tag']}#{c['id'] or ''} .{c['classes'][:80]}>")
                    print(f"        right={c['right']}px  width={c['width']}px  left={c['left']}px")
                    print(f"        computed-width={c['computed_width']}  position={c['computed_position']}")
                    print(f"        overflow={c['computed_overflow']}  parent-overflow={c['parent_overflow']}")
                    print(f"        inline: {c['inline_style'][:100]}")
                # Screenshot
                slug = rel.replace("/", "_").replace(".html", "")
                shot_path = SCREENSHOT_DIR / f"step1_{slug}_{vp_w}px.png"
                await page.screenshot(path=str(shot_path), full_page=False)
                print(f"        Screenshot: {shot_path.name}")
            except Exception as e:
                print(f"    [{vp_w}px] ERROR: {e}")
            finally:
                await ctx.close()


async def step2_motion_effects(browser):
    print("\n" + "="*70)
    print("STEP 2 — MOTION-EFFECTS LAYER: REAL BUG vs FALSE POSITIVE")
    print("="*70)

    for rel, url_path in MOTION_EFFECTS_PAGES:
        url = BASE_URL + url_path
        print(f"\n  PAGE: {rel}")
        for vp_w in [375, 768, 1440]:
            ctx = await browser.new_context(
                viewport={"width": vp_w, "height": 900},
                ignore_https_errors=True,
            )
            page = await ctx.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(400)
                result = await page.evaluate(MOTION_EFFECTS_INSPECT_JS)
                page_scroll = result.get("page_has_horizontal_scrollbar")
                layers = result.get("layers", [])
                print(f"    [{vp_w}px] page_has_horizontal_scrollbar={page_scroll}  layers_found={len(layers)}")
                for i, lay in enumerate(layers):
                    print(f"      Layer {i+1}:")
                    print(f"        size: {lay['layer_width']}px  computed-width: {lay['layer_width_computed']}")
                    print(f"        position: {lay['layer_position']}  transform: {lay['layer_transform'][:60] if lay['layer_transform'] else 'none'}")
                    print(f"        overflow_past_viewport: {lay['overflow_past_viewport']}px")
                    print(f"        parent ({lay['parent_tag']}.{(lay['parent_classes'] or '')[:60]})")
                    print(f"          overflow: {lay['parent_overflow']}  right: {lay['parent_right']}px")
                    print(f"          overflow_past_parent: {lay['overflow_past_parent']}px")
                    print(f"        grandparent overflow: {lay['grandparent_overflow']}")
                # Screenshot at 768px (worst case from audit)
                if vp_w == 768:
                    slug = rel.replace("/", "_").replace(".html", "").strip("_")
                    shot_path = SCREENSHOT_DIR / f"step2_{slug}_{vp_w}px.png"
                    await page.screenshot(path=str(shot_path), full_page=False)
                    print(f"      Screenshot: {shot_path.name}")
            except Exception as e:
                print(f"    [{vp_w}px] ERROR: {e}")
            finally:
                await ctx.close()


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    print("K Techara — Overflow Validation Script")
    print(f"Screenshots -> {SCREENSHOT_DIR}")

    server = start_server()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            await step1_strict_overflow(browser)
            await step2_motion_effects(browser)
            await browser.close()
    finally:
        server.terminate()

    print("\nDone. Review findings and screenshots above.")

if __name__ == "__main__":
    asyncio.run(main())
