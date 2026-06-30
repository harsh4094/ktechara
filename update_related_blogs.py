#!/usr/bin/env python3
"""Replace Related insights sections with Related blogs on Our Solutions pages."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
BLOG_DATA = ROOT / 'data' / 'blog-posts.json'
OUR_SOLUTIONS = ROOT / 'our-solutions'

LOOP_CONTAINER_RE = re.compile(
    r'(<div class="elementor-loop-container elementor-grid" role="list">)(.*?)(</div>\s*\n\s*\n\s*</div>\s*\n\s*</div>)',
    re.DOTALL,
)
LOOP_ITEM_RE = re.compile(
    r'<div data-elementor-type="loop-item"[\s\S]*?(?=<div data-elementor-type="loop-item"|</div>\s*\n\s*\n\s*</div>)',
)


def depth_prefix(html_path: Path) -> str:
    rel = html_path.relative_to(ROOT)
    parts = list(rel.parts[:-1])  # drop filename
    return '../' * len(parts)


def rel_path(prefix: str, path: str) -> str:
    if path.startswith('/'):
        return prefix + path.lstrip('/')
    return prefix + path


def card_html(post: dict, prefix: str) -> str:
    blog_index = rel_path(prefix, 'blog/index.html')
    post_url = rel_path(prefix, post['url'])
    img = rel_path(prefix, post['image'].lstrip('/'))
    srcset = ', '.join(
        f"{rel_path(prefix, part.strip().split()[0].lstrip('/'))} {part.strip().split()[1]}"
        if len(part.strip().split()) == 2
        else rel_path(prefix, part.strip().lstrip('/'))
        for part in post['srcset'].split(',')
    )
    title = post['title']
    pid = post['id']

    return f'''                            <div data-elementor-type="loop-item" data-elementor-id="31654" class="elementor elementor-31654 e-loop-item e-loop-item-{pid} post-{pid} insights type-insights status-publish format-standard has-post-thumbnail hentry insights-type-blog" data-elementor-post-type="elementor_library" data-custom-edit-handle="1">
                                <div class="elementor-element elementor-element-393ea075 e-con-full e-flex e-con e-parent" data-id="393ea075" data-element_type="container" data-e-type="container" data-settings="{{&quot;background_background&quot;:&quot;classic&quot;}}">
                                    <div class="elementor-element elementor-element-2f1ecd58 e-con-full e-flex e-con e-child" data-id="2f1ecd58" data-element_type="container" data-e-type="container" data-settings="{{&quot;background_background&quot;:&quot;classic&quot;}}">
                                        <div class="elementor-element elementor-element-30810b99 e-con-full e-flex e-con e-child" data-id="30810b99" data-element_type="container" data-e-type="container" data-settings="{{&quot;background_background&quot;:&quot;classic&quot;}}">
                                            <div class="elementor-element elementor-element-68057356 type-title elementor-widget elementor-widget-post-info" data-id="68057356" data-element_type="widget" data-e-type="widget" data-widget_type="post-info.default">
                                                <ul class="elementor-inline-items elementor-icon-list-items elementor-post-info">
                                                    <li class="elementor-icon-list-item elementor-repeater-item-7166291 elementor-inline-item" itemprop="about">
                                                        <span class="elementor-icon-list-text elementor-post-info__item elementor-post-info__item--type-terms">
                                                            <span class="elementor-post-info__terms-list">
                                                                <a href="{blog_index}" class="elementor-post-info__terms-list-item" data-wpel-link="internal">Blog</a> </span>
                                                        </span>
                                                    </li>
                                                </ul>
                                            </div>
                                            <div class="elementor-element elementor-element-73d44d2c rltcase elementor-widget elementor-widget-heading" data-id="73d44d2c" data-element_type="widget" data-e-type="widget" data-widget_type="heading.default">
                                                <h4 class="elementor-heading-title elementor-size-default"><a href="{post_url}" data-wpel-link="internal">{title}</a></h4>
                                            </div>
                                        </div>
                                        <div class="elementor-element elementor-element-54bf3100 e-flex e-con-boxed e-con e-child" data-id="54bf3100" data-element_type="container" data-e-type="container" data-settings="{{&quot;background_background&quot;:&quot;classic&quot;}}">
                                            <div class="e-con-inner">
                                                <div class="elementor-element elementor-element-5ee84178 elementor-widget elementor-widget-theme-post-featured-image elementor-widget-image" data-id="5ee84178" data-element_type="widget" data-e-type="widget" data-widget_type="theme-post-featured-image.default">
                                                    <a href="{post_url}" data-wpel-link="internal">
                                                        <img loading="lazy" decoding="async" width="{post['width']}" height="{post['height']}" src="{img}" class="elementor-animation-grow attachment-large size-large wp-image-{pid + 2}" alt="" srcset="{srcset}" sizes="(max-width: 800px) 100vw, 800px" /> </a>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>'''


def replace_loop_items(content: str, prefix: str, posts: list) -> str:
    def replacer(match):
        opening = match.group(1)
        inner = match.group(2)
        closing = match.group(3)
        style_match = re.search(r'<style id="loop-31654">[\s\S]*?</style>', inner)
        style_block = style_match.group(0) if style_match else ''
        cards = '\n'.join(card_html(p, prefix) for p in posts[:3])
        return opening + '\n' + style_block + '\n' + cards + '\n                        ' + closing

    return LOOP_CONTAINER_RE.sub(replacer, content, count=1)


def update_file(path: Path, posts: list) -> bool:
    text = path.read_text(encoding='utf-8', errors='replace')
    if 'Related insights' not in text and 'id="insights"' not in text:
        return False

    prefix = depth_prefix(path)
    updated = text
    updated = updated.replace('Related insights', 'Related blogs')
    updated = replace_loop_items(updated, prefix, posts)

    if updated != text:
        path.write_text(updated, encoding='utf-8')
        return True
    return False


def main():
    posts = json.loads(BLOG_DATA.read_text(encoding='utf-8'))
    changed = []
    for html_path in sorted(OUR_SOLUTIONS.rglob('*.html')):
        if update_file(html_path, posts):
            changed.append(html_path.relative_to(ROOT))

    print(f'Updated {len(changed)} file(s):')
    for p in changed:
        print(f'  - {p}')


if __name__ == '__main__':
    main()
