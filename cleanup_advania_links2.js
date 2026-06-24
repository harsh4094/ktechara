#!/usr/bin/env node
/**
 * Phase 2 cleanup:
 *  1. Download all wp-includes/js/* files locally + update all HTML references
 *  2. Fix remaining cdn-cgi email-protection with data-cfemail attribute pattern
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
          headers: { 'User-Agent': 'Mozilla/5.0 Chrome/124.0.0.0', 'Accept': '*/*' },
        }, (res) => {
          if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location)
            return fetchBuffer(res.headers.location, retries - 1).then(resolve);
          const chunks = [];
          res.on('data', c => chunks.push(c));
          res.on('end', () => resolve(Buffer.concat(chunks)));
        });
        req.on('error', e => n < retries ? setTimeout(() => attempt(n + 1), 1500) : resolve(null));
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

// All wp-includes/js files to download
const WP_JS_FILES = [
  { url: 'https://ktechara.co.uk/wp-includes/js/jquery/jquery.min.js?ver=3.7.1',
    local: 'wp-content/wp-includes/js/jquery/jquery.min.js',
    pattern: /https?:\/\/www\.advania\.co\.uk\/wp-includes\/js\/jquery\/jquery\.min\.js[^"']*/g },
  { url: 'https://ktechara.co.uk/wp-includes/js/jquery/jquery-migrate.min.js?ver=3.4.1',
    local: 'wp-content/wp-includes/js/jquery/jquery-migrate.min.js',
    pattern: /https?:\/\/www\.advania\.co\.uk\/wp-includes\/js\/jquery\/jquery-migrate\.min\.js[^"']*/g },
  { url: 'https://ktechara.co.uk/wp-includes/js/jquery/ui/core.min.js?ver=1.13.3',
    local: 'wp-content/wp-includes/js/jquery/ui/core.min.js',
    pattern: /https?:\/\/www\.advania\.co\.uk\/wp-includes\/js\/jquery\/ui\/core\.min\.js[^"']*/g },
  { url: 'https://ktechara.co.uk/wp-includes/js/dist/hooks.min.js?ver=dd5603f07f9220ed27f1',
    local: 'wp-content/wp-includes/js/dist/hooks.min.js',
    pattern: /https?:\/\/www\.advania\.co\.uk\/wp-includes\/js\/dist\/hooks\.min\.js[^"']*/g },
  { url: 'https://ktechara.co.uk/wp-includes/js/dist/i18n.min.js?ver=c26c3dc7bed366793375',
    local: 'wp-content/wp-includes/js/dist/i18n.min.js',
    pattern: /https?:\/\/www\.advania\.co\.uk\/wp-includes\/js\/dist\/i18n\.min\.js[^"']*/g },
  { url: 'https://ktechara.co.uk/wp-includes/js/imagesloaded.min.js?ver=5.0.0',
    local: 'wp-content/wp-includes/js/imagesloaded.min.js',
    pattern: /https?:\/\/www\.advania\.co\.uk\/wp-includes\/js\/imagesloaded\.min\.js[^"']*/g },
  { url: 'https://ktechara.co.uk/wp-includes/js/mediaelement/mediaelement-and-player.min.js?ver=4.2.17',
    local: 'wp-content/wp-includes/js/mediaelement/mediaelement-and-player.min.js',
    pattern: /https?:\/\/www\.advania\.co\.uk\/wp-includes\/js\/mediaelement\/mediaelement-and-player\.min\.js[^"']*/g },
  { url: 'https://ktechara.co.uk/wp-includes/js/mediaelement/mediaelement-migrate.min.js?ver=6.9.4',
    local: 'wp-content/wp-includes/js/mediaelement/mediaelement-migrate.min.js',
    pattern: /https?:\/\/www\.advania\.co\.uk\/wp-includes\/js\/mediaelement\/mediaelement-migrate\.min\.js[^"']*/g },
  { url: 'https://ktechara.co.uk/wp-includes/js/mediaelement/renderers/vimeo.min.js?ver=4.2.17',
    local: 'wp-content/wp-includes/js/mediaelement/renderers/vimeo.min.js',
    pattern: /https?:\/\/www\.advania\.co\.uk\/wp-includes\/js\/mediaelement\/renderers\/vimeo\.min\.js[^"']*/g },
  { url: 'https://ktechara.co.uk/wp-includes/js/mediaelement/wp-mediaelement.min.js?ver=6.9.4',
    local: 'wp-content/wp-includes/js/mediaelement/wp-mediaelement.min.js',
    pattern: /https?:\/\/www\.advania\.co\.uk\/wp-includes\/js\/mediaelement\/wp-mediaelement\.min\.js[^"']*/g },
];

async function main() {
  console.log('=== Phase 2: wp-includes/js + remaining email cleanup ===\n');

  // Step 1: Download all wp-includes/js files
  console.log('Downloading wp-includes/js files...');
  for (const entry of WP_JS_FILES) {
    const fullPath = path.join(ROOT, entry.local);
    fs.mkdirSync(path.dirname(fullPath), { recursive: true });

    if (fs.existsSync(fullPath) && fs.statSync(fullPath).size > 100) {
      console.log(`  [cached] ${entry.local}`);
      continue;
    }

    const data = await fetchBuffer(entry.url);
    if (data && data.length > 100) {
      fs.writeFileSync(fullPath, data);
      console.log(`  Downloaded: ${entry.local} (${data.length} bytes)`);
    } else {
      console.error(`  FAILED: ${entry.url}`);
    }
    await sleep(100);
  }

  // Step 2: Process all HTML files
  console.log('\nProcessing HTML files...');
  const htmlFiles = findHtmlFiles(ROOT);
  let jsFilesFixed = 0;
  let emailDataFixed = 0;

  for (const filePath of htmlFiles) {
    let content = fs.readFileSync(filePath, 'utf8');
    const original = content;

    // Replace wp-includes/js external references with local paths
    if (content.includes('advania.co.uk/wp-includes/js')) {
      for (const entry of WP_JS_FILES) {
        if (entry.pattern.test(content)) {
          entry.pattern.lastIndex = 0;
          const local = relPath(filePath, entry.local);
          content = content.replace(entry.pattern, local);
        }
        entry.pattern.lastIndex = 0;
      }
      if (content !== original) jsFilesFixed++;
    }

    // Fix remaining cdn-cgi with data-cfemail attribute pattern:
    // <a href="https://ktechara.co.uk/cdn-cgi/l/email-protection" class="__cf_email__" data-cfemail="HASH">text</a>
    if (content.includes('cdn-cgi/l/email-protection') && content.includes('data-cfemail')) {
      const before = content;
      content = content.replace(
        /<a href="https:\/\/www\.advania\.co\.uk\/cdn-cgi\/l\/email-protection"\s+class="__cf_email__"\s+data-cfemail="([a-f0-9]+)">[^<]*<\/a>/g,
        (match, hash) => {
          const email = cfDecodeEmail(hash);
          return `<a href="mailto:${email}">${email}</a>`;
        }
      );
      // Also handle href-only version (no class/data, just the bare href="...#hash")
      // These should already be fixed by phase 1, but catch any that have the bare href pattern
      content = content.replace(
        /href="https:\/\/www\.advania\.co\.uk\/cdn-cgi\/l\/email-protection#([a-f0-9]+)"/g,
        (match, hash) => {
          const email = cfDecodeEmail(hash);
          return `href="mailto:${email}"`;
        }
      );
      if (content !== before) emailDataFixed++;
    }

    if (content !== original) {
      fs.writeFileSync(filePath, content, 'utf8');
    }
  }

  console.log(`  wp-includes/js replaced:  ${jsFilesFixed} files`);
  console.log(`  data-cfemail decoded:     ${emailDataFixed} files`);

  // Final verification
  console.log('\n=== Final verification ===');
  const remainingCdnCgi = htmlFiles.filter(f => fs.readFileSync(f,'utf8').includes('cdn-cgi/l/email-protection'));
  const remainingWpJs = htmlFiles.filter(f => fs.readFileSync(f,'utf8').includes('advania.co.uk/wp-includes/js'));
  const remainingWpIncludes = htmlFiles.filter(f => fs.readFileSync(f,'utf8').includes('advania.co.uk/wp-includes'));

  console.log(`  cdn-cgi/email-protection remaining: ${remainingCdnCgi.length}`);
  if (remainingCdnCgi.length > 0 && remainingCdnCgi.length <= 10)
    remainingCdnCgi.forEach(f => console.log(`    ${path.relative(ROOT, f)}`));

  console.log(`  advania.co.uk/wp-includes remaining: ${remainingWpIncludes.length}`);
  if (remainingWpIncludes.length > 0 && remainingWpIncludes.length <= 5)
    remainingWpIncludes.forEach(f => console.log(`    ${path.relative(ROOT, f)}`));

  // Show what advania.co.uk references remain in total (as src= or href= to load assets)
  const assetSrcRemaining = htmlFiles.filter(f => {
    const c = fs.readFileSync(f,'utf8');
    return /src="https?:\/\/(?:www\.)?advania\.co\.uk/.test(c) ||
           /href="https?:\/\/(?:www\.)?advania\.co\.uk\/wp-includes/.test(c);
  });
  console.log(`\n  External advania.co.uk asset/script loads remaining: ${assetSrcRemaining.length}`);
  if (assetSrcRemaining.length > 0 && assetSrcRemaining.length <= 10)
    assetSrcRemaining.forEach(f => {
      const c = fs.readFileSync(f,'utf8');
      const m = c.match(/src="https?:\/\/(?:www\.)?advania\.co\.uk[^"]*"/);
      console.log(`    ${path.relative(ROOT, f)}: ${m ? m[0].substring(0,80) : ''}`);
    });
}

main().catch(e => { console.error(e); process.exit(1); });
