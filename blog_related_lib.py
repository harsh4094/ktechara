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
