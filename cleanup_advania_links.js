#!/usr/bin/env node
/**
 * Final cleanup: remove all remaining advania.co.uk references that are
 * external dependencies (not content hyperlinks to external pages).
 *
 * Actions:
 *  1. wp-block-library CSS  → download locally + update 32 files
 *  2. cdn-cgi email-protection links → decode to real mailto: links (614 files)
 *  3. http://advania.co.uk bare logo links → replace with "/" (23 files)
 *  4. info.advania.co.uk/hubfs/logo-advania.svg → download + replace (23 files)
 *  5. advania.co.uk page links that exist locally → replace with relative paths
 *     (privacy-policy, terms-of-use, cookie-notice, anti-slavery-statement,
 *      code-of-conduct → /complaints-code/, sustainability)
 *  6. feed/ atom:link self-refs → update to relative (archive-feeds XML files)
 *  7. advania.co.uk/wp-content/uploads/...pdf → keep (external PDF, no local copy)
 *  8. advania.co.uk/contact-us/ → replace with /contact-us/ (local page exists)
 *  9. advania.co.uk/insights/blog/... → replace with local relative path
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const ROOT = __dirname;

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fetchBuffer(fetchUrl, retries = 3) {
  return new Promise((resolve) => {
    const attempt = (n) => {
      try {
        const parsedUrl = new url.URL(fetchUrl);
        const lib = parsedUrl.protocol === 'https:' ? https : http;
        const req = lib.request({
          hostname: parsedUrl.hostname,
          path: parsedUrl.pathname + parsedUrl.search,
          method: 'GET',
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0',
            'Accept': '*/*',
          },
        }, (res) => {
          if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
            return fetchBuffer(res.headers.location, retries - 1).then(resolve);
          }
          const chunks = [];
          res.on('data', c => chunks.push(c));
          res.on('end', () => resolve(Buffer.concat(chunks)));
        });
        req.on('error', e => {
          if (n < retries) setTimeout(() => attempt(n + 1), 1500);
          else resolve(null);
        });
        req.setTimeout(20000, () => req.destroy());
        req.end();
      } catch (e) { resolve(null); }
    };
    attempt(1);
  });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function cfDecodeEmail(enc) {
  let r = parseInt(enc.substr(0, 2), 16), e = '';
  for (let n = 2; n < enc.length; n += 2)
    e += String.fromCharCode(parseInt(enc.substr(n, 2), 16) ^ r);
  return e;
}

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

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  console.log('=== Final advania.co.uk link cleanup ===\n');

  // ── Step 1: Download wp-block-library CSS ──────────────────────────────────
  const wpBlockLocalPath = 'wp-content/wp-includes/css/block-library/style.min.css';
  const wpBlockFullPath = path.join(ROOT, wpBlockLocalPath);
  fs.mkdirSync(path.dirname(wpBlockFullPath), { recursive: true });

  if (!fs.existsSync(wpBlockFullPath) || fs.statSync(wpBlockFullPath).size < 100) {
    console.log('Downloading wp-block-library CSS...');
    const data = await fetchBuffer(
      'https://ktechara.co.uk/wp-includes/css/dist/block-library/style.min.css?ver=6.9.4'
    );
    if (data && data.length > 100) {
      fs.writeFileSync(wpBlockFullPath, data);
      console.log(`  Saved: ${wpBlockLocalPath} (${data.length} bytes)`);
    } else {
      console.error('  FAILED to download wp-block-library CSS');
    }
  } else {
    console.log(`  [cached] ${wpBlockLocalPath}`);
  }

  // ── Step 2: Download info.advania.co.uk/hubfs/logo-advania.svg ─────────────
  const logoSvgLocalPath = 'wp-content/uploads/hubspot/logo-advania.svg';
  const logoSvgFullPath = path.join(ROOT, logoSvgLocalPath);

  if (!fs.existsSync(logoSvgFullPath) || fs.statSync(logoSvgFullPath).size < 10) {
    console.log('Downloading logo-advania.svg...');
    const data = await fetchBuffer('https://info.advania.co.uk/hubfs/logo-advania.svg');
    if (data && data.length > 10) {
      fs.writeFileSync(logoSvgFullPath, data);
      console.log(`  Saved: ${logoSvgLocalPath} (${data.length} bytes)`);
    } else {
      console.error('  FAILED to download logo-advania.svg');
    }
  } else {
    console.log(`  [cached] ${logoSvgLocalPath}`);
  }

  // ── Step 3: Process all HTML files ────────────────────────────────────────
  console.log('\nScanning HTML files...');
  const htmlFiles = findHtmlFiles(ROOT);
  console.log(`Found ${htmlFiles.length} files\n`);

  const stats = {
    wpBlockCSS: 0,
    emailProtection: 0,
    bareAdvaniaLink: 0,
    logoSvg: 0,
    pageLinks: 0,
    feedLinks: 0,
    contactUs: 0,
    insightsBlog: 0,
  };

  for (const filePath of htmlFiles) {
    let content = fs.readFileSync(filePath, 'utf8');
    const original = content;

    // 1. Replace wp-block-library external CSS
    if (content.includes('advania.co.uk/wp-includes/css')) {
      const local = relPath(filePath, wpBlockLocalPath);
      content = content.replace(
        /https:\/\/www\.advania\.co\.uk\/wp-includes\/css\/dist\/block-library\/style\.min\.css\?ver=[^"]+/g,
        local
      );
      if (content !== original) stats.wpBlockCSS++;
    }

    // 2. Decode Cloudflare email-protection links
    if (content.includes('cdn-cgi/l/email-protection')) {
      let changed = false;
      content = content.replace(
        /https:\/\/www\.advania\.co\.uk\/cdn-cgi\/l\/email-protection#([a-f0-9]+)/g,
        (match, hash) => {
          const email = cfDecodeEmail(hash);
          changed = true;
          return 'mailto:' + email;
        }
      );
      // Also fix the bare /cdn-cgi/l/email-protection without hash (used as href="...#...")
      if (changed) stats.emailProtection++;
    }

    // 3. Replace bare http://advania.co.uk logo links with "/"
    if (content.includes('"http://advania.co.uk"')) {
      content = content.replace(/"http:\/\/advania\.co\.uk"/g, '"/"');
      stats.bareAdvaniaLink++;
    }
    if (content.includes('"https://advania.co.uk"')) {
      content = content.replace(/"https:\/\/advania\.co\.uk"/g, '"/"');
    }
    if (content.includes('"https://ktechara.co.uk"')) {
      content = content.replace(/"https:\/\/www\.advania\.co\.uk"/g, '"/"');
    }

    // 4. Replace info.advania.co.uk/hubfs/logo-advania.svg with local path
    if (content.includes('info.advania.co.uk/hubfs/logo-advania.svg')) {
      const local = relPath(filePath, logoSvgLocalPath);
      content = content.replace(/https:\/\/info\.advania\.co\.uk\/hubfs\/logo-advania\.svg/g, local);
      stats.logoSvg++;
    }

    // 5. Replace advania.co.uk page links that exist locally
    const pageReplacements = [
      // privacy-policy
      [/https?:\/\/(?:www\.)?advania\.co\.uk\/privacy-policy\/?/g, '/privacy-policy/'],
      // terms-of-use
      [/https?:\/\/(?:www\.)?advania\.co\.uk\/terms-of-use\/?/g, '/terms-of-use/'],
      // cookie-notice page removed — redirect old links to privacy-policy
      [/https?:\/\/(?:www\.)?advania\.co\.uk\/cookie-notice\/?/g, '/privacy-policy/'],
      // anti-slavery-statement
      [/https?:\/\/(?:www\.)?advania\.co\.uk\/anti-slavery-statement\/?/g, '/anti-slavery-statement/'],
      // code-of-conduct → complaints-code (closest local equivalent)
      [/https?:\/\/(?:www\.)?advania\.co\.uk\/code-of-conduct\/?/g, '/complaints-code/'],
      // sustainability
      [/https?:\/\/(?:www\.)?advania\.co\.uk\/sustainability\/?/g, '/sustainability/'],
      // contact-us (strip UTM and keep /contact-us/)
      [/https?:\/\/(?:www\.)?advania\.co\.uk\/contact-us\/[^"']*/g, '/contact-us/'],
      // insights/blog pages
      [/https?:\/\/(?:www\.)?advania\.co\.uk\/insights\/blog\/([^"'?#]*)/g, '/insights/blog/$1'],
    ];

    let pageBefore = content;
    for (const [pattern, replacement] of pageReplacements) {
      content = content.replace(pattern, replacement);
    }
    if (content !== pageBefore) stats.pageLinks++;

    // 6. Fix feed atom:link self-references (XML files in archive-feeds)
    if (content.includes('advania.co.uk') && content.includes('atom:link') && content.includes('feed/')) {
      content = content.replace(
        /https?:\/\/(?:www\.)?advania\.co\.uk\/((?:[^"]*?)feed\/)/g,
        '/$1'
      );
      stats.feedLinks++;
    }

    // Write back if changed
    if (content !== original) {
      fs.writeFileSync(filePath, content, 'utf8');
    }
  }

  console.log('=== Results ===');
  console.log(`  wp-block-library CSS replaced:     ${stats.wpBlockCSS} files`);
  console.log(`  Email protection decoded:           ${stats.emailProtection} files`);
  console.log(`  Bare advania.co.uk links fixed:     ${stats.bareAdvaniaLink} files`);
  console.log(`  logo-advania.svg replaced:          ${stats.logoSvg} files`);
  console.log(`  Page links → local paths:           ${stats.pageLinks} files`);
  console.log(`  Feed self-links fixed:              ${stats.feedLinks} files`);

  // Final verification
  console.log('\n=== Final verification ===');
  const checks = [
    ['advania.co.uk/wp-includes', 'wp-includes CSS external'],
    ['cdn-cgi/l/email-protection', 'Cloudflare email protection'],
    ['"http://advania.co.uk"', 'bare logo link http'],
    ['info.advania.co.uk/hubfs/logo-advania.svg', 'logo SVG external'],
  ];
  for (const [needle, label] of checks) {
    const files = findHtmlFiles(ROOT).filter(f => fs.readFileSync(f,'utf8').includes(needle));
    console.log(`  ${files.length === 0 ? '✓' : '✗'} ${label}: ${files.length} files remaining`);
    if (files.length > 0 && files.length <= 5) files.forEach(f => console.log(`      ${path.relative(ROOT,f)}`));
  }

  // Full advania.co.uk external asset/script count (should be 0)
  let remaining = 0;
  const remainingFiles = [];
  const assetPatterns = [
    /src="https?:\/\/(?:www\.)?advania\.co\.uk/,
    /href="https?:\/\/(?:www\.)?advania\.co\.uk\/wp-includes/,
    /href="https?:\/\/(?:www\.)?advania\.co\.uk\/wp-content\/plugins/,
    /url\(['"]https?:\/\/(?:www\.)?advania\.co\.uk/,
  ];
  for (const filePath of findHtmlFiles(ROOT)) {
    const c = fs.readFileSync(filePath, 'utf8');
    if (assetPatterns.some(p => p.test(c))) {
      remaining++;
      remainingFiles.push(path.relative(ROOT, filePath));
    }
  }
  console.log(`\n  ${remaining === 0 ? '✓' : '✗'} External advania.co.uk asset/script src: ${remaining} files`);
  if (remainingFiles.length > 0 && remainingFiles.length <= 10) {
    remainingFiles.forEach(f => console.log(`      ${f}`));
  }
}

main().catch(e => { console.error(e); process.exit(1); });
