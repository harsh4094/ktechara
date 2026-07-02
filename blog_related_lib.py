"""Shared text-processing helpers for converting blog post 'related articles'
sections from hardcoded News/Event cards into randomized Blog cards."""
import re
from pathlib import Path

TITLE_SUFFIX_RE = re.compile(r"\s*[-–|]\s*K\s*Techara(\s*UK)?\s*$", re.IGNORECASE)
POSTID_RE = re.compile(r"postid-(\d+)")
TITLE_TAG_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL)
OG_IMAGE_RE = re.compile(r'property="og:image"\s+content="([^"]+)"')
OG_IMAGE_WIDTH_RE = re.compile(r'property="og:image:width"\s+content="([^"]+)"')
OG_IMAGE_HEIGHT_RE = re.compile(r'property="og:image:height"\s+content="([^"]+)"')


def clean_title(raw_title: str) -> str:
    collapsed = re.sub(r"\s+", " ", raw_title).strip()
    return TITLE_SUFFIX_RE.sub("", collapsed).strip()


def extract_post_data(html_text: str) -> dict | None:
    postid_m = POSTID_RE.search(html_text)
    title_m = TITLE_TAG_RE.search(html_text)
    image_m = OG_IMAGE_RE.search(html_text)
    if not (postid_m and title_m and image_m):
        return None

    width_m = OG_IMAGE_WIDTH_RE.search(html_text)
    height_m = OG_IMAGE_HEIGHT_RE.search(html_text)

    return {
        "id": int(postid_m.group(1)),
        "title": clean_title(title_m.group(1)),
        "image": image_m.group(1),
        "width": int(width_m.group(1)) if width_m else 1200,
        "height": int(height_m.group(1)) if height_m else 600,
    }


def find_srcset(image_path: str, width: int, project_root) -> str | None:
    rel = image_path.lstrip("/")
    full_path = Path(project_root) / rel
    base, ext = full_path.stem, full_path.suffix

    variants = {(image_path, width)}
    pattern = re.compile(rf"^{re.escape(base)}-(\d+)x(\d+){re.escape(ext)}$")
    for sibling in full_path.parent.glob(f"{base}-*x*{ext}"):
        m = pattern.match(sibling.name)
        if not m:
            continue
        sibling_width = int(m.group(1))
        rel_variant = "/" + sibling.relative_to(project_root).as_posix()
        variants.add((rel_variant, sibling_width))

    if len(variants) == 1:
        return None

    ordered = sorted(variants, key=lambda t: t[1])
    return ", ".join(f"{path} {w}w" for path, w in ordered)


def _prefix_url(url: str, prefix: str) -> str:
    return prefix + url.lstrip("/")


def _prefix_srcset(srcset: str, prefix: str) -> str:
    entries = []
    for entry in srcset.split(", "):
        path, width_token = entry.rsplit(" ", 1)
        entries.append(f"{_prefix_url(path, prefix)} {width_token}")
    return ", ".join(entries)


def build_card_html(post: dict, prefix: str) -> str:
    post_href = _prefix_url(post["url"], prefix)
    img_src = _prefix_url(post["image"], prefix)
    blog_href = prefix + "blog/index.html"

    extra_img_attrs = ""
    if post.get("srcset"):
        srcset_val = _prefix_srcset(post["srcset"], prefix)
        extra_img_attrs = (
            f'\n                                srcset="{srcset_val}"'
            f'\n                                sizes="(max-width: {post["width"]}px) 100vw, {post["width"]}px"'
        )

    return f'''                <div
                  data-elementor-type="loop-item"
                  data-elementor-id="31654"
                  class="elementor elementor-31654 e-loop-item e-loop-item-{post['id']} post-{post['id']} insights type-insights status-publish format-standard has-post-thumbnail hentry insights-type-blog"
                  data-elementor-post-type="elementor_library"
                  data-custom-edit-handle="1"
                >
                  <div
                    class="elementor-element elementor-element-393ea075 e-con-full e-flex e-con e-parent"
                    data-id="393ea075"
                    data-element_type="container"
                    data-e-type="container"
                    data-settings='{{"background_background":"classic"}}'
                  >
                    <div
                      class="elementor-element elementor-element-2f1ecd58 e-con-full e-flex e-con e-child"
                      data-id="2f1ecd58"
                      data-element_type="container"
                      data-e-type="container"
                      data-settings='{{"background_background":"classic"}}'
                    >
                      <div
                        class="elementor-element elementor-element-30810b99 e-con-full e-flex e-con e-child"
                        data-id="30810b99"
                        data-element_type="container"
                        data-e-type="container"
                        data-settings='{{"background_background":"classic"}}'
                      >
                        <div
                          class="elementor-element elementor-element-68057356 type-title elementor-widget elementor-widget-post-info"
                          data-id="68057356"
                          data-element_type="widget"
                          data-e-type="widget"
                          data-widget_type="post-info.default"
                        >
                          <ul
                            class="elementor-inline-items elementor-icon-list-items elementor-post-info"
                          >
                            <li
                              class="elementor-icon-list-item elementor-repeater-item-7166291 elementor-inline-item"
                              itemprop="about"
                            >
                              <span
                                class="elementor-icon-list-text elementor-post-info__item elementor-post-info__item--type-terms"
                              >
                                <span class="elementor-post-info__terms-list">
                                  <a
                                    href="{blog_href}"
                                    class="elementor-post-info__terms-list-item"
                                    data-wpel-link="internal"
                                    >Blog</a
                                  >
                                </span>
                              </span>
                            </li>
                          </ul>
                        </div>
                        <div
                          class="elementor-element elementor-element-73d44d2c rltcase elementor-widget elementor-widget-heading"
                          data-id="73d44d2c"
                          data-element_type="widget"
                          data-e-type="widget"
                          data-widget_type="heading.default"
                        >
                          <h4
                            class="elementor-heading-title elementor-size-default"
                          >
                            <a
                              href="{post_href}"
                              data-wpel-link="internal"
                              >{post['title']}</a
                            >
                          </h4>
                        </div>
                      </div>
                      <div
                        class="elementor-element elementor-element-54bf3100 e-flex e-con-boxed e-con e-child"
                        data-id="54bf3100"
                        data-element_type="container"
                        data-e-type="container"
                        data-settings='{{"background_background":"classic"}}'
                      >
                        <div class="e-con-inner">
                          <div
                            class="elementor-element elementor-element-5ee84178 elementor-widget elementor-widget-theme-post-featured-image elementor-widget-image"
                            data-id="5ee84178"
                            data-element_type="widget"
                            data-e-type="widget"
                            data-widget_type="theme-post-featured-image.default"
                          >
                            <a
                              href="{post_href}"
                              data-wpel-link="internal"
                            >
                              <img
                                loading="lazy"
                                width="{post['width']}"
                                height="{post['height']}"
                                src="{img_src}"
                                class="elementor-animation-grow attachment-full size-full wp-image-{post['id']}"
                                alt=""{extra_img_attrs}
                              />
                            </a>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>'''
