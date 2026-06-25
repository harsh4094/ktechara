#!/usr/bin/env python3
"""
Cleanup script for _header.html and _footer.html.
Run from the repo root: python clean_nav.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent


def empty_ul(html, ul_id):
    pattern = rf'(<ul id="{ul_id}"[^>]*>)\s*(?:<li\b[^>]*>.*?</li>\s*)*(</ul>)'
    result, n = re.subn(pattern, r'\1\2', html, count=1, flags=re.DOTALL)
    if n == 0:
        print(f'  WARNING: ul#{ul_id} not found')
    return result


def remove_li_with_href(html, href):
    pattern = rf'<li\b[^>]*>\s*<a\s[^>]*href="{re.escape(href)}"[^>]*>.*?</a>\s*</li>'
    result, n = re.subn(pattern, '', html, flags=re.DOTALL)
    if n == 0:
        print(f'  WARNING: li href={href!r} not found')
    return result


header_path = ROOT / '_header.html'
footer_path = ROOT / '_footer.html'
header = header_path.read_text(encoding='utf-8')
footer = footer_path.read_text(encoding='utf-8')

print('Processing _header.html ...')

# 1. Fix dead hrefs
for old, new in [
    ('/technology-sourcing.1.html',              '/technology-sourcing/index.html'),
    ('/our-solutions.html',                      '/our-solutions/index.html'),
    ('/our-services.html',                       '/our-services/index.html'),
    ('/solutions-by-sector.html',                '/solutions-by-sector/index.html'),
    ('/about-us.1.html',                         '/about-us/index.html'),
    ('/about-us/ecosystem-and-partners/index.html', '/partners/index.html'),
    ('/talk-to-an-expert.html',                  '/contact-us/index.html'),
]:
    c = header.count(f'href="{old}"')
    header = header.replace(f'href="{old}"', f'href="{new}"')
    print(f'  href fix x{c}: {old}')

# 2. Empty dead sub-link menus
for uid in [
    'menu-1-10539fda', 'menu-2-10539fda',  # WHAT WE DO: Tech Sourcing
    'menu-1-c8a61d2',  'menu-2-c8a61d2',   # WHAT WE DO: Solutions
    'menu-1-45e16c08', 'menu-2-45e16c08',  # WHAT WE DO: Services
    'menu-1-f8e9328',  'menu-2-f8e9328',   # SECTORS col 1
    'menu-1-83f0f69',  'menu-2-83f0f69',   # SECTORS col 2
    'menu-1-b7155c9',  'menu-2-b7155c9',   # Partners col 1
    'menu-1-46023c3',  'menu-2-46023c3',   # Partners col 2
    'menu-1-51b09d4e', 'menu-2-51b09d4e',  # About Us col 2 (all dead)
]:
    header = empty_ul(header, uid)

# 3. Remove dead items from About Us first col (keep About K Techara + Case Studies)
for href in ['/about-us/people-culture-and-careers/index.html',
             '/sustainability/index.html']:
    header = remove_li_with_href(header, href)
    print(f'  removed About Us dead li: {href}')

# 4. Simplify Insights dropdown to Blog + News only
INSIGHTS_SIMPLE = (
    '                                            <div class="e-n-menu-content">\n'
    '                                                <div id="e-n-menu-content-1524" data-tab-index="4" aria-labelledby="e-n-menu-dropdown-icon-1524" class="elementor-element elementor-element-1b075d47 e-con-full e-flex e-con e-child" data-id="1b075d47" data-element_type="container" data-e-type="container" data-settings="{&quot;background_background&quot;:&quot;classic&quot;}">\n'
    '                                                    <div class="elementor-element elementor-element-c823a84 e-con-full e-flex e-con e-child" data-id="c823a84" data-element_type="container" data-e-type="container">\n'
    '                                                        <div class="elementor-element elementor-element-34bbdcf7 e-flex e-con-boxed e-con e-child" data-id="34bbdcf7" data-element_type="container" data-e-type="container" data-settings="{&quot;background_background&quot;:&quot;classic&quot;}">\n'
    '                                                            <div class="e-con-inner">\n'
    '                                                                <div class="elementor-element elementor-element-6ee22b9d e-con-full e-flex e-con e-child" data-id="6ee22b9d" data-element_type="container" data-e-type="container">\n'
    '                                                                    <div class="elementor-element elementor-element-1a4717e4 elementor-nav-menu--dropdown-none elementor-widget elementor-widget-nav-menu" data-id="1a4717e4" data-element_type="widget" data-e-type="widget" data-settings="{&quot;layout&quot;:&quot;vertical&quot;,&quot;submenu_icon&quot;:{&quot;value&quot;:&quot;&lt;i class=\\&quot;fas fa-caret-down\\&quot; aria-hidden=\\&quot;true\\&quot;&gt;&lt;\\/i&gt;&quot;,&quot;library&quot;:&quot;fa-solid&quot;}}" data-widget_type="nav-menu.default">\n'
    '                                                                        <nav aria-label="Menu" class="elementor-nav-menu--main elementor-nav-menu__container elementor-nav-menu--layout-vertical e--pointer-none">\n'
    '                                                                            <ul id="menu-1-1a4717e4" class="elementor-nav-menu sm-vertical">\n'
    '                                                                                <li class="menu-item menu-item-type-custom menu-item-object-custom menu-item-31868">\n'
    '                                                                                    <a href="/blog/index.html" class="elementor-item" data-wpel-link="internal">Blog</a>\n'
    '                                                                                </li>\n'
    '                                                                                <li class="menu-item menu-item-type-custom menu-item-object-custom menu-item-31869">\n'
    '                                                                                    <a href="/news/index.html" class="elementor-item" data-wpel-link="internal">News</a>\n'
    '                                                                                </li>\n'
    '                                                                            </ul>\n'
    '                                                                        </nav>\n'
    '                                                                        <nav class="elementor-nav-menu--dropdown elementor-nav-menu__container" aria-hidden="true">\n'
    '                                                                            <ul id="menu-2-1a4717e4" class="elementor-nav-menu sm-vertical">\n'
    '                                                                                <li class="menu-item menu-item-type-custom menu-item-object-custom menu-item-31868">\n'
    '                                                                                    <a href="/blog/index.html" class="elementor-item" tabindex="-1" data-wpel-link="internal">Blog</a>\n'
    '                                                                                </li>\n'
    '                                                                                <li class="menu-item menu-item-type-custom menu-item-object-custom menu-item-31869">\n'
    '                                                                                    <a href="/news/index.html" class="elementor-item" tabindex="-1" data-wpel-link="internal">News</a>\n'
    '                                                                                </li>\n'
    '                                                                            </ul>\n'
    '                                                                        </nav>\n'
    '                                                                    </div>\n'
    '                                                                </div>\n'
    '                                                            </div>\n'
    '                                                        </div>\n'
    '                                                    </div>\n'
    '                                                </div>\n'
    '                                            </div>'
)

insights_start = (
    '                                            <div class="e-n-menu-content">\n'
    '                                                <div id="e-n-menu-content-1524"'
)
about_us_start = (
    '                                        <li class="e-n-menu-item">\n'
    '                                            <div id="e-n-menu-title-1525"'
)
si = header.find(insights_start)
ai = header.find(about_us_start)
if si != -1 and ai != -1:
    close_marker = '                                        </li>'
    cl = header.rfind(close_marker, si, ai)
    if cl != -1:
        end = cl + len(close_marker)
        header = header[:si] + INSIGHTS_SIMPLE + '\n' + header[end:]
        print('  Insights simplified to Blog + News')
    else:
        print('  WARNING: Insights </li> close not found')
else:
    print(f'  WARNING: Insights anchors not found (si={si}, ai={ai})')

header_path.write_text(header, encoding='utf-8')
print(f'  Written ({len(header)} bytes)')

print('\nProcessing _footer.html ...')

# 1. Fix dead hrefs
for old, new in [
    ('/technology-sourcing.1.html',              '/technology-sourcing/index.html'),
    ('/about-us/ecosystem-and-partners/index.html', '/partners/index.html'),
    ('/our-solutions.html',                      '/our-solutions/index.html'),
    ('/our-services.html',                       '/our-services/index.html'),
    ('/solutions-by-sector.html',                '/solutions-by-sector/index.html'),
    ('/about-us.1.html',                         '/about-us/index.html'),
    ('/about-us/microsoft-partnership.1.html',   '/about-us/index.html'),
    ('/set-up-a-meeting/ .1.html',               '/contact-us/index.html'),
]:
    c = footer.count(f'href="{old}"')
    footer = footer.replace(f'href="{old}"', f'href="{new}"')
    print(f'  href fix x{c}: {old}')

# 2. Empty all dead nav menus
for uid in [
    'menu-1-5efceb18', 'menu-2-5efceb18',   # Desktop: Tech Sourcing
    'menu-1-1048b09a', 'menu-2-1048b09a',   # Desktop: Partners
    'menu-1-67150256', 'menu-2-67150256',   # Desktop: Solutions
    'menu-1-3ab3bf38', 'menu-2-3ab3bf38',   # Desktop: About Us col 2
    'menu-1-65ed2c06', 'menu-2-65ed2c06',   # Desktop: Services
    'menu-1-565b2a75', 'menu-2-565b2a75',   # Desktop: Sectors col 1
    'menu-1-2b68c5e6', 'menu-2-2b68c5e6',   # Desktop: Sectors col 2
    'menu-1-220a8288', 'menu-2-220a8288',   # Mobile: Tech Sourcing
    'menu-1-563d770a', 'menu-2-563d770a',   # Mobile: Solutions
    'menu-1-6a9fe2e',  'menu-2-6a9fe2e',    # Mobile: Services
    'menu-1-2f2b7c60', 'menu-2-2f2b7c60',   # Mobile: Sectors
    'menu-1-447c1622', 'menu-2-447c1622',   # Mobile: Partners
    'menu-1-2ce8079',  'menu-2-2ce8079',    # Mobile: About Us col 2
]:
    footer = empty_ul(footer, uid)

# 3. Remove dead items from About Us first col (keep About K Techara + Case Studies)
for href in ['/about-us/people-culture-and-careers/index.html',
             '/sustainability/index.html']:
    footer = remove_li_with_href(footer, href)
    print(f'  removed About Us dead li: {href}')

footer_path.write_text(footer, encoding='utf-8')
print(f'  Written ({len(footer)} bytes)')

print('\nDone. Now run: python build_header_footer.py')
