#!/usr/bin/env node
/**
 * Download all advania.co.uk/wp-content/uploads/* images that are missing locally,
 * then update HTML src= references to use local relative paths.
 * Also fixes the 2 mediaelement CSS files and remaining wp-includes CSS.
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const ROOT = __dirname;

function fetchBuffer(fetchUrl, retries = 3) {
  return new Promise((resolve) => {
    const attempt = (n) => {
      try {
        const p = new url.URL(fetchUrl);
        const lib = p.protocol === 'https:' ? https : http;
        const req = lib.request({
          hostname: p.hostname, path: p.pathname + p.search, method: 'GET',
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/avif,image/*,*/*;q=0.8',
            'Referer': 'https://ktechara.co.uk/',
          },
        }, (res) => {
          if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location)
            return fetchBuffer(res.headers.location, retries - 1).then(resolve);
          if (res.statusCode === 404) { resolve(null); return; }
          const chunks = [];
          res.on('data', c => chunks.push(c));
          res.on('end', () => resolve(Buffer.concat(chunks)));
        });
        req.on('error', e => n < retries ? setTimeout(() => attempt(n + 1), 1500) : resolve(null));
        req.setTimeout(25000, () => req.destroy());
        req.end();
      } catch (e) { resolve(null); }
    };
    attempt(1);
  });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

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

async function main() {
  console.log('=== Download missing wp-content/uploads images ===\n');

  const htmlFiles = findHtmlFiles(ROOT);

  // Collect all unique advania.co.uk/wp-content/uploads URLs
  console.log('Scanning for external wp-content/uploads references...');
  const urlMap = new Map(); // external URL base (no query) -> local path from root

  const globalRe = /src="(https?:\/\/(?:www\.)?advania\.co\.uk\/wp-content\/uploads\/[^"?]+)(?:[^"]*)?"/ ;
  for (const filePath of htmlFiles) {
    const content = fs.readFileSync(filePath, 'utf8');
    const re = new RegExp(globalRe.source, 'g');
    let m;
    while ((m = re.exec(content)) !== null) {
      const imgUrl = m[1];
      if (!urlMap.has(imgUrl)) {
        const localPath = imgUrl
          .replace(/https?:\/\/(?:www\.)?advania\.co\.uk\//, '')
          .split('?')[0];
        urlMap.set(imgUrl, localPath);
      }
    }
  }

  console.log(`Found ${urlMap.size} unique wp-content/uploads image URLs\n`);

  // Download missing files
  let downloaded = 0;
  let cached = 0;
  const failed = [];

  for (const [imgUrl, localPath] of urlMap) {
    const fullPath = path.join(ROOT, localPath);
    fs.mkdirSync(path.dirname(fullPath), { recursive: true });

    if (fs.existsSync(fullPath) && fs.statSync(fullPath).size > 100) {
      cached++;
      continue;
    }

    const data = await fetchBuffer(imgUrl);
    if (data && data.length > 100) {
      fs.writeFileSync(fullPath, data);
      downloaded++;
      if (downloaded % 10 === 0) console.log(`  [${downloaded}] Downloaded ${localPath}`);
    } else {
      failed.push(imgUrl);
      if (failed.length <= 10) console.error(`  FAILED: ${imgUrl}`);
    }
    await sleep(80);
  }

  console.log(`\nDownloaded: ${downloaded}, Cached: ${cached}, Failed: ${failed.length}`);
  if (failed.length > 10) console.log(`  (${failed.length - 10} more failures not shown)`);

  // ── Also download mediaelement CSS files ──────────────────────────────────
  const mediaCssFiles = [
    {
      url: 'https://ktechara.co.uk/wp-includes/js/mediaelement/mediaelementplayer-legacy.min.css?ver=4.2.17',
      local: 'wp-content/wp-includes/js/mediaelement/mediaelementplayer-legacy.min.css',
    },
    {
      url: 'https://ktechara.co.uk/wp-includes/js/mediaelement/wp-mediaelement.min.css?ver=6.9.4',
      local: 'wp-content/wp-includes/js/mediaelement/wp-mediaelement.min.css',
    },
  ];
  console.log('\nDownloading mediaelement CSS files...');
  for (const entry of mediaCssFiles) {
    const fullPath = path.join(ROOT, entry.local);
    fs.mkdirSync(path.dirname(fullPath), { recursive: true });
    if (fs.existsSync(fullPath) && fs.statSync(fullPath).size > 10) {
      console.log(`  [cached] ${entry.local}`);
      continue;
    }
    const data = await fetchBuffer(entry.url);
    if (data && data.length > 10) {
      fs.writeFileSync(fullPath, data);
      console.log(`  Downloaded: ${entry.local}`);
    } else {
      console.error(`  FAILED: ${entry.url}`);
    }
  }

  // ── Update HTML files ─────────────────────────────────────────────────────
  console.log('\nUpdating HTML references...');
  let filesUpdated = 0;

  for (const filePath of htmlFiles) {
    let content = fs.readFileSync(filePath, 'utf8');
    const original = content;

    // Replace all external wp-content/uploads src references
    if (content.includes('advania.co.uk/wp-content/uploads')) {
      for (const [imgUrl, localPath] of urlMap) {
        if (!content.includes(imgUrl)) continue;
        // Escape URL for regex
        const escaped = imgUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        // Match URL with optional query string
        const re = new RegExp(escaped + '(?:\\?[^"\'\\s)>]*)?', 'g');
        const local = relPath(filePath, localPath);
        content = content.replace(re, local);
      }
    }

    // Fix mediaelement CSS
    if (content.includes('advania.co.uk/wp-includes/js/mediaelement')) {
      for (const entry of mediaCssFiles) {
        const escaped = entry.url.split('?')[0].replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const re = new RegExp(escaped + '(?:\\?[^"]*)?', 'g');
        content = content.replace(re, relPath(filePath, entry.local));
      }
    }

    if (content !== original) {
      fs.writeFileSync(filePath, content, 'utf8');
      filesUpdated++;
    }
  }
  console.log(`Updated ${filesUpdated} HTML files`);

  // ── Final verification ────────────────────────────────────────────────────
  console.log('\n=== FINAL COMPLETE VERIFICATION ===');
  const checks = [
    ['advania.co.uk/wp-content/uploads', 'wp-content/uploads external images'],
    ['advania.co.uk/wp-includes', 'wp-includes external assets'],
    ['cdn-cgi/l/email-protection', 'Cloudflare email protection'],
    ['use.typekit.net', 'Typekit external'],
    ['googletagmanager.com', 'Google Tag Manager'],
    ['gmpg.org', 'gmpg profile link'],
    ['wpenginepowered.com', 'WP Engine staging'],
    ['_hcms/cookie-banner', 'HubSpot cookie banner'],
    ['info.advania.co.uk/hs-fs/hubfs', 'HubSpot hs-fs images'],
  ];

  let allClear = true;
  for (const [needle, label] of checks) {
    const count = htmlFiles.filter(f => fs.readFileSync(f,'utf8').includes(needle)).length;
    const ok = count === 0;
    if (!ok) allClear = false;
    console.log(`  ${ok ? '✓' : '✗'} ${label}: ${count} files`);
  }
  console.log(allClear ? '\n✓ All external dependencies cleared!' : '\n⚠ Some dependencies remain');
}

main().catch(e => { console.error(e); process.exit(1); });
