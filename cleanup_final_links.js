#!/usr/bin/env node
/**
 * Final pass: remove ALL remaining https://ktechara.co.uk/ references from HTML files.
 *
 * Handles:
 *  1. og:url / og:image / msapplication-TileImage content= meta tags → strip domain
 *  2. ajaxurl: "https://ktechara.co.uk/wp-admin/admin-ajax.php" → "/wp-admin/admin-ajax.php"
 *  3. href= Elementor CSS (wp-content/uploads/elementor/css/post-*.css) → depth-relative local path
 *  4. href= Premium Addons CSS (wp-content/uploads/premium-addons-elementor/pafe-*.css) → depth-relative
 *  5. CSS sourceURL comments → strip entirely
 *  6. href= navigation page links → strip domain, keep path root-relative
 *  7. ?post_type=insights&p=XXXXX draft preview URLs → /insights/
 *  8. content="https://ktechara.co.uk" bare domain in meta → "/"
 *  9. Any remaining https://ktechara.co.uk/wp-content/uploads/ in content= → strip domain
 * 10. Any remaining href="https://ktechara.co.uk/..." navigation links → strip domain
 * 11. ajaxurl in WP inline scripts (all forms) → /wp-admin/admin-ajax.php
 * 12. CSS url() advania references inside <style> blocks → strip domain
 * 13. data-permalink / data-url advania attributes → strip domain
 */

const fs = require('fs');
const path = require('path');

const ROOT = __dirname;

function findHtmlFiles(dir) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory() && entry.name !== '.git') results.push(...findHtmlFiles(full));
    else if (entry.isFile() && entry.name.endsWith('.html')) results.push(full);
  }
  return results;
}

function getDepth(filePath) {
  return path.relative(ROOT, filePath).split(path.sep).length - 1;
}

function relPath(filePath, localFromRoot) {
  const depth = getDepth(filePath);
  return (depth === 0 ? '' : '../'.repeat(depth)) + localFromRoot;
}

const stats = {
  ogUrl: 0, ogImage: 0, ajaxurl: 0, elementorCss: 0, pafeCss: 0,
  sourceUrl: 0, navLinks: 0, draftLinks: 0, bareContent: 0, dataAttrs: 0, styleBlock: 0,
};

function processFile(filePath, content) {
  let c = content;

  // ── 1. og:url content= → strip domain, keep path ──────────────────────────
  // <meta property="og:url" content="https://ktechara.co.uk/some/path/" />
  if (c.includes('og:url') && c.includes('advania.co.uk')) {
    const before = c;
    c = c.replace(
      /(<meta\s[^>]*property="og:url"[^>]*content=")https?:\/\/(?:www\.)?advania\.co\.uk([^"]*?)(")/g,
      (m, pre, path_, post) => pre + (path_ || '/') + post
    );
    c = c.replace(
      /(<meta\s[^>]*content=")https?:\/\/(?:www\.)?advania\.co\.uk([^"]*?)("\s[^>]*property="og:url")/g,
      (m, pre, path_, post) => pre + (path_ || '/') + post
    );
    if (c !== before) stats.ogUrl++;
  }

  // ── 2. og:image / msapplication-TileImage content= → strip domain ─────────
  if (c.includes('advania.co.uk/wp-content') && (c.includes('og:image') || c.includes('msapplication-TileImage') || c.includes('twitter:image'))) {
    const before = c;
    c = c.replace(
      /(<meta\s[^>]*(og:image|msapplication-TileImage|twitter:image)[^>]*content=")https?:\/\/(?:www\.)?advania\.co\.uk(\/wp-content[^"]*?)(")/g,
      (m, pre, _prop, imgPath, post) => pre + imgPath + post
    );
    c = c.replace(
      /(<meta\s[^>]*content=")https?:\/\/(?:www\.)?advania\.co\.uk(\/wp-content[^"]*?)("[^>]*(og:image|msapplication-TileImage|twitter:image))/g,
      (m, pre, imgPath, post, _prop) => pre + imgPath + post
    );
    if (c !== before) stats.ogImage++;
  }

  // ── 3. ajaxurl in all JS contexts → /wp-admin/admin-ajax.php ───────────────
  if (c.includes('advania.co.uk/wp-admin/admin-ajax.php')) {
    const before = c;
    c = c.replace(
      /https?:\/\/(?:www\.)?advania\.co\.uk\/wp-admin\/admin-ajax\.php/g,
      '/wp-admin/admin-ajax.php'
    );
    if (c !== before) stats.ajaxurl++;
  }

  // ── 4. Elementor CSS href= → depth-relative local path ────────────────────
  if (c.includes('advania.co.uk/wp-content/uploads/elementor/css/')) {
    const before = c;
    c = c.replace(
      /https?:\/\/(?:www\.)?advania\.co\.uk\/(wp-content\/uploads\/elementor\/css\/[^"'?]+)(?:\?[^"']*)?/g,
      (m, localFromRoot) => relPath(filePath, localFromRoot)
    );
    if (c !== before) stats.elementorCss++;
  }

  // ── 5. Premium Addons CSS href= → depth-relative local path ───────────────
  if (c.includes('advania.co.uk/wp-content/uploads/premium-addons-elementor/')) {
    const before = c;
    c = c.replace(
      /https?:\/\/(?:www\.)?advania\.co\.uk\/(wp-content\/uploads\/premium-addons-elementor\/[^"'?]+)(?:\?[^"']*)?/g,
      (m, localFromRoot) => relPath(filePath, localFromRoot)
    );
    if (c !== before) stats.pafeCss++;
  }

  // ── 6. CSS sourceURL comments → remove ────────────────────────────────────
  if (c.includes('sourceURL=https://ktechara.co.uk')) {
    const before = c;
    c = c.replace(/\/\*#\s*sourceURL=https?:\/\/(?:www\.)?advania\.co\.uk[^*]*\*\//g, '');
    if (c !== before) stats.sourceUrl++;
  }

  // ── 7. draft/preview ?post_type=insights&p=XXXXX → /insights/ ────────────
  if (c.includes('post_type=insights')) {
    const before = c;
    c = c.replace(
      /https?:\/\/(?:www\.)?advania\.co\.uk\/[^"']*\?post_type=insights[^"']*/g,
      '/insights/'
    );
    if (c !== before) stats.draftLinks++;
  }

  // ── 8. bare content="https://ktechara.co.uk" → "/" ─────────────────────
  if (c.includes('content="https://ktechara.co.uk"') || c.includes("content='https://ktechara.co.uk'")) {
    const before = c;
    c = c.replace(/content="https?:\/\/(?:www\.)?advania\.co\.uk"/g, 'content="/"');
    c = c.replace(/content='https?:\/\/(?:www\.)?advania\.co\.uk'/g, "content='/'");
    if (c !== before) stats.bareContent++;
  }

  // ── 9. Remaining wp-content/uploads in content= meta tags → strip domain ──
  if (c.includes('advania.co.uk/wp-content/uploads')) {
    const before = c;
    // In content="" attributes (not src= which was already handled)
    c = c.replace(
      /content="https?:\/\/(?:www\.)?advania\.co\.uk(\/wp-content\/uploads\/[^"?]+)(?:\?[^"]*)?"/ ,
      (m, imgPath) => `content="${imgPath}"`
    );
    // global replacement
    c = c.replace(
      /content="https?:\/\/(?:www\.)?advania\.co\.uk(\/wp-content\/uploads\/[^"?]+)(?:\?[^"]*)?" /g,
      (m, imgPath) => `content="${imgPath}" `
    );
    if (c !== before) stats.ogImage++;
  }

  // ── 10. href= navigation links → strip domain, keep path root-relative ────
  if (c.includes('href="https://ktechara.co.uk/') || c.includes("href='https://ktechara.co.uk/")) {
    const before = c;
    // Strip domain from all href="https://ktechara.co.uk/PATH" links
    // (NOT matching just "https://ktechara.co.uk" bare — those were handled above)
    c = c.replace(
      /href="https?:\/\/(?:www\.)?advania\.co\.uk(\/[^"#?]*)(?:[^"]*)?"([^>]*>)/g,
      (m, urlPath, rest) => {
        // Keep query strings and hash, just strip domain
        const fullMatch = m;
        const domainStripped = fullMatch.replace(/href="https?:\/\/(?:www\.)?advania\.co\.uk/, 'href="');
        return domainStripped;
      }
    );
    c = c.replace(
      /href='https?:\/\/(?:www\.)?advania\.co\.uk(\/[^'#?]*)(?:[^']*)?'([^>]*>)/g,
      (m, urlPath, rest) => {
        return m.replace(/href='https?:\/\/(?:www\.)?advania\.co\.uk/, "href='");
      }
    );
    if (c !== before) stats.navLinks++;
  }

  // ── 11. CSS url() inside <style> blocks → strip domain ────────────────────
  if (c.includes('advania.co.uk') && (c.includes('<style') || c.includes('url('))) {
    const before = c;
    c = c.replace(
      /url\(['"]?https?:\/\/(?:www\.)?advania\.co\.uk(\/[^'")]+)['"]?\)/g,
      (m, urlPath) => `url('${urlPath}')`
    );
    if (c !== before) stats.styleBlock++;
  }

  // ── 12. data-permalink / data-url / data-link attributes ──────────────────
  if (c.includes('advania.co.uk')) {
    const before = c;
    c = c.replace(
      /(data-(?:permalink|url|link|href|canonical|og-url)=")https?:\/\/(?:www\.)?advania\.co\.uk(\/[^"]*?)"/g,
      (m, attr, urlPath) => `${attr}${urlPath}"`
    );
    if (c !== before) stats.dataAttrs++;
  }

  // ── 13. wp-content/uploads/elementor/css/ in <link> href with full URL ─────
  // Catch any remaining ones not caught by step 4 (e.g. with ver= in middle)
  if (c.includes('advania.co.uk/wp-content/uploads/elementor')) {
    c = c.replace(
      /https?:\/\/(?:www\.)?advania\.co\.uk\/(wp-content\/uploads\/elementor\/[^"'?]+)(?:\?[^"']*)?/g,
      (m, localFromRoot) => relPath(filePath, localFromRoot)
    );
  }

  // ── 14. wp-content/plugins CSS or JS → strip domain ──────────────────────
  if (c.includes('advania.co.uk/wp-content/plugins')) {
    c = c.replace(
      /https?:\/\/(?:www\.)?advania\.co\.uk\/(wp-content\/plugins\/[^"'?]+)(?:\?[^"']*)?/g,
      (m, localFromRoot) => '/' + localFromRoot
    );
  }

  // ── 15. Any remaining advania.co.uk/wp-content/themes → strip domain ──────
  if (c.includes('advania.co.uk/wp-content/themes')) {
    c = c.replace(
      /https?:\/\/(?:www\.)?advania\.co\.uk\/(wp-content\/themes\/[^"'?]+)(?:\?[^"']*)?/g,
      (m, localFromRoot) => relPath(filePath, localFromRoot)
    );
  }

  // ── 16. Catch-all: remaining meta content= with advania domain ────────────
  if (c.includes('advania.co.uk')) {
    c = c.replace(
      /(<meta\s[^>]*content=")https?:\/\/(?:www\.)?advania\.co\.uk(\/[^"]*?)"/g,
      (m, pre, urlPath) => `${pre}${urlPath}"`
    );
    // Also content= with no path (bare domain)
    c = c.replace(
      /(<meta\s[^>]*content=")https?:\/\/(?:www\.)?advania\.co\.uk"/g,
      (m, pre) => `${pre}/"`
    );
  }

  return c;
}

async function main() {
  console.log('=== Final cleanup: all remaining advania.co.uk references ===\n');

  const htmlFiles = findHtmlFiles(ROOT);
  console.log(`Processing ${htmlFiles.length} HTML files...\n`);

  let filesModified = 0;

  for (const filePath of htmlFiles) {
    const original = fs.readFileSync(filePath, 'utf8');

    if (!original.includes('advania.co.uk')) continue;

    const updated = processFile(filePath, original);

    if (updated !== original) {
      fs.writeFileSync(filePath, updated, 'utf8');
      filesModified++;
    }
  }

  console.log(`Files modified: ${filesModified}\n`);
  console.log('=== Changes by type ===');
  console.log(`  og:url meta fixed:              ${stats.ogUrl}`);
  console.log(`  og:image/TileImage fixed:       ${stats.ogImage}`);
  console.log(`  ajaxurl fixed:                  ${stats.ajaxurl}`);
  console.log(`  Elementor CSS href fixed:       ${stats.elementorCss}`);
  console.log(`  Premium Addons CSS href fixed:  ${stats.pafeCss}`);
  console.log(`  CSS sourceURL stripped:         ${stats.sourceUrl}`);
  console.log(`  Nav/page links stripped:        ${stats.navLinks}`);
  console.log(`  Draft preview links fixed:      ${stats.draftLinks}`);
  console.log(`  Bare content= domain fixed:     ${stats.bareContent}`);
  console.log(`  data-* attrs fixed:             ${stats.dataAttrs}`);
  console.log(`  CSS url() in style fixed:       ${stats.styleBlock}`);

  // Verification
  console.log('\n=== Verification: remaining advania.co.uk references ===');

  const remaining = [];
  let totalRefs = 0;
  for (const filePath of htmlFiles) {
    const c = fs.readFileSync(filePath, 'utf8');
    if (c.includes('advania.co.uk')) {
      // Count occurrences
      const matches = c.match(/advania\.co\.uk/g);
      totalRefs += matches ? matches.length : 0;
      remaining.push({ file: path.relative(ROOT, filePath), count: matches ? matches.length : 0 });
    }
  }

  console.log(`\nTotal files still containing "advania.co.uk": ${remaining.length}`);
  console.log(`Total occurrences: ${totalRefs}\n`);

  // Categorize remaining references
  const cats = {
    'community.advania.co.uk (nav links — intentional)': 0,
    'belong.advania.co.uk (careers — intentional)': 0,
    'info.advania.co.uk/_hcms/forms (HubSpot forms — intentional)': 0,
    'info.advania.co.uk/ebook (external ebooks — intentional)': 0,
    'info.advania.co.uk/engagement (external engagement — intentional)': 0,
    'advania.co.uk text in content (not href/src)': 0,
    'OTHER (unexpected)': 0,
  };

  for (const filePath of htmlFiles) {
    const c = fs.readFileSync(filePath, 'utf8');
    if (!c.includes('advania.co.uk')) continue;

    const lines = c.split('\n');
    for (const line of lines) {
      if (!line.includes('advania.co.uk')) continue;

      if (line.includes('community.advania.co.uk')) { cats['community.advania.co.uk (nav links — intentional)']++; continue; }
      if (line.includes('belong.advania.co.uk')) { cats['belong.advania.co.uk (careers — intentional)']++; continue; }
      if (line.includes('info.advania.co.uk/_hcms/forms')) { cats['info.advania.co.uk/_hcms/forms (HubSpot forms — intentional)']++; continue; }
      if (line.includes('info.advania.co.uk/ebook')) { cats['info.advania.co.uk/ebook (external ebooks — intentional)']++; continue; }
      if (line.includes('info.advania.co.uk/engagement')) { cats['info.advania.co.uk/engagement (external engagement — intentional)']++; continue; }
      if (line.includes('info.advania.co.uk/hubspot-training') || line.includes('info.advania.co.uk/resources') || line.includes('info.advania.co.uk/thank-you') || line.includes('info.advania.co.uk/')) {
        cats['info.advania.co.uk/ebook (external ebooks — intentional)']++;
        continue;
      }
      // Check if it's a plain text reference (in content, not in a tag attribute)
      if (!line.match(/(?:href|src|content|url\(|@import)=['"]/)) {
        cats['advania.co.uk text in content (not href/src)']++;
        continue;
      }
      cats['OTHER (unexpected)']++;
    }
  }

  for (const [cat, count] of Object.entries(cats)) {
    if (count > 0) console.log(`  ${count.toString().padStart(6)} : ${cat}`);
  }

  // Show sample of any unexpected remaining
  console.log('\n=== Sample unexpected remaining (if any) ===');
  let shown = 0;
  for (const filePath of htmlFiles) {
    if (shown >= 20) break;
    const c = fs.readFileSync(filePath, 'utf8');
    if (!c.includes('advania.co.uk')) continue;
    const lines = c.split('\n');
    for (const [i, line] of lines.entries()) {
      if (shown >= 20) break;
      if (!line.includes('advania.co.uk')) continue;
      if (line.includes('community.advania.co.uk')) continue;
      if (line.includes('belong.advania.co.uk')) continue;
      if (line.includes('info.advania.co.uk')) continue;
      if (!line.match(/(?:href|src|content|url\(|@import)=['"]/)) continue;
      console.log(`  ${path.relative(ROOT, filePath)}:${i + 1}: ${line.trim().substring(0, 120)}`);
      shown++;
    }
  }
  if (shown === 0) console.log('  None — all remaining references are intentional external links.');

  console.log('\nDone.');
}

main().catch(e => { console.error(e); process.exit(1); });
