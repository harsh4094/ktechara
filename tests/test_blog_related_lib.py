import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from blog_related_lib import (
    clean_title,
    extract_post_data,
    find_srcset,
    build_card_html,
    replace_related_section,
)


class CleanTitleTests(unittest.TestCase):
    def test_strips_k_techara_suffix(self):
        self.assertEqual(clean_title("How Power Apps work - K Techara"), "How Power Apps work")

    def test_strips_k_techara_uk_suffix(self):
        self.assertEqual(
            clean_title("Cyber security AI from Inspire's news - K Techara UK"),
            "Cyber security AI from Inspire's news",
        )

    def test_strips_en_dash_suffix(self):
        self.assertEqual(
            clean_title("Which digital tools are best – K Techara"),
            "Which digital tools are best",
        )

    def test_strips_pipe_suffix(self):
        self.assertEqual(
            clean_title("Empowering our colleagues through Women Rising | K Techara"),
            "Empowering our colleagues through Women Rising",
        )

    def test_no_suffix_is_left_unchanged(self):
        self.assertEqual(clean_title("Staff Turnover Risk"), "Staff Turnover Risk")

    def test_collapses_multiline_whitespace(self):
        raw = "\n      How to build a relationship with an AI\n    "
        self.assertEqual(clean_title(raw), "How to build a relationship with an AI")


class ExtractPostDataTests(unittest.TestCase):
    def make_html(self, postid='postid-28004', title='<title>How to build a relationship with an AI</title>',
                  og_image='<meta property="og:image" content="/wp-content/uploads/2024/03/pic.png" />',
                  og_width='<meta property="og:image:width" content="1200" />',
                  og_height='<meta property="og:image:height" content="600" />'):
        return f'''<!doctype html>
<html><head>
{title}
{og_image}
{og_width}
{og_height}
</head><body class="wp-singular single {postid} single-format-standard">
</body></html>'''

    def test_extracts_all_fields(self):
        data = extract_post_data(self.make_html())
        self.assertEqual(data, {
            "id": 28004,
            "title": "How to build a relationship with an AI",
            "image": "/wp-content/uploads/2024/03/pic.png",
            "width": 1200,
            "height": 600,
        })

    def test_defaults_width_height_when_missing(self):
        html = self.make_html(og_width='', og_height='')
        data = extract_post_data(html)
        self.assertEqual(data["width"], 1200)
        self.assertEqual(data["height"], 600)

    def test_handles_multiline_title_tag(self):
        html = self.make_html(title='<title>\n      How Power Apps work - K Techara\n    </title>')
        data = extract_post_data(html)
        self.assertEqual(data["title"], "How Power Apps work")

    def test_returns_none_when_postid_missing(self):
        html = self.make_html(postid='no-post-id-here')
        self.assertIsNone(extract_post_data(html))

    def test_returns_none_when_og_image_missing(self):
        html = self.make_html(og_image='')
        self.assertIsNone(extract_post_data(html))


class FindSrcsetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.img_dir = self.root / "wp-content" / "uploads" / "2024" / "03"
        self.img_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_none_when_no_variants_exist(self):
        (self.img_dir / "pic.png").write_bytes(b"x")
        result = find_srcset("/wp-content/uploads/2024/03/pic.png", 1200, self.root)
        self.assertIsNone(result)

    def test_builds_srcset_from_variants_ascending_by_width(self):
        (self.img_dir / "pic.png").write_bytes(b"x")
        (self.img_dir / "pic-1024x512.png").write_bytes(b"x")
        (self.img_dir / "pic-300x150.png").write_bytes(b"x")
        (self.img_dir / "pic-768x384.png").write_bytes(b"x")
        result = find_srcset("/wp-content/uploads/2024/03/pic.png", 1200, self.root)
        self.assertEqual(
            result,
            "/wp-content/uploads/2024/03/pic-300x150.png 300w, "
            "/wp-content/uploads/2024/03/pic-768x384.png 768w, "
            "/wp-content/uploads/2024/03/pic-1024x512.png 1024w, "
            "/wp-content/uploads/2024/03/pic.png 1200w",
        )

    def test_ignores_unrelated_files_in_same_directory(self):
        (self.img_dir / "pic.png").write_bytes(b"x")
        (self.img_dir / "other-picture-300x150.png").write_bytes(b"x")
        result = find_srcset("/wp-content/uploads/2024/03/pic.png", 1200, self.root)
        self.assertIsNone(result)


class BuildCardHtmlTests(unittest.TestCase):
    def test_card_without_srcset(self):
        post = {
            "id": 28004,
            "title": "How to build a relationship with an AI",
            "url": "blog/agility/building-relationship-ai/index.html",
            "image": "/wp-content/uploads/2024/03/pic.png",
            "width": 1200,
            "height": 600,
            "srcset": None,
        }
        html = build_card_html(post, "../../../")
        self.assertIn('e-loop-item-28004 post-28004', html)
        self.assertIn('insights-type-blog', html)
        self.assertIn('href="../../../blog/agility/building-relationship-ai/index.html"', html)
        self.assertIn('>How to build a relationship with an AI<', html)
        self.assertIn('href="../../../blog/index.html"', html)
        self.assertIn('>Blog<', html)
        self.assertIn('src="../../../wp-content/uploads/2024/03/pic.png"', html)
        self.assertIn('width="1200"', html)
        self.assertIn('height="600"', html)
        self.assertNotIn('srcset=', html)

    def test_card_with_srcset_prefixes_every_entry(self):
        post = {
            "id": 33690,
            "title": "AI &amp; the enterprise",
            "url": "blog/data/ai-and-the-enterprise/index.html",
            "image": "/wp-content/uploads/2024/03/pic.png",
            "width": 1200,
            "height": 600,
            "srcset": "/wp-content/uploads/2024/03/pic-300x150.png 300w, /wp-content/uploads/2024/03/pic.png 1200w",
        }
        html = build_card_html(post, "../../../")
        self.assertIn(
            'srcset="../../../wp-content/uploads/2024/03/pic-300x150.png 300w, '
            '../../../wp-content/uploads/2024/03/pic.png 1200w"',
            html,
        )
        self.assertIn('sizes="(max-width: 1200px) 100vw, 1200px"', html)
        self.assertIn('>AI &amp; the enterprise<', html)


FIXTURE_PAGE = '''<!doctype html>
<html><body>
<div class="page-content">Article body here.</div>
<div class="elementor-element elementor-element-541f7e1 e-con">
  <div class="e-con-inner">
    <div class="heading-wrap">
      <h3 class="elementor-heading-title elementor-size-default">
        Other articles that might interest you
      </h3>
    </div>
    <div class="elementor-element elementor-element-4d017d1 elementor-widget-loop-grid">
      <div class="elementor-widget-container">
        <div class="elementor-loop-container elementor-grid" role="list">
          <style id="loop-31654">.elementor-31654 { color: red; }</style>
          <div data-elementor-type="loop-item" data-elementor-id="31654" class="old-card-1">
            <div class="inner-1">News card one</div>
          </div>
          <div data-elementor-type="loop-item" data-elementor-id="31654" class="old-card-2">
            <div class="inner-2">Event card two</div>
          </div>
          <div data-elementor-type="loop-item" data-elementor-id="31654" class="old-card-3">
            <div class="inner-3">Event card three</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
</body></html>'''


class ReplaceRelatedSectionTests(unittest.TestCase):
    def test_replaces_heading_text(self):
        result = replace_related_section(FIXTURE_PAGE, "NEW_CARDS_PLACEHOLDER")
        self.assertNotIn("Other articles that might interest you", result)
        self.assertIn("Related blogs", result)

    def test_replaces_all_three_old_cards_with_new_ones(self):
        result = replace_related_section(FIXTURE_PAGE, "NEW_CARDS_PLACEHOLDER")
        self.assertNotIn("old-card-1", result)
        self.assertNotIn("old-card-2", result)
        self.assertNotIn("old-card-3", result)
        self.assertNotIn("News card one", result)
        self.assertEqual(result.count("NEW_CARDS_PLACEHOLDER"), 1)

    def test_preserves_style_block_and_surrounding_structure(self):
        result = replace_related_section(FIXTURE_PAGE, "NEW_CARDS_PLACEHOLDER")
        self.assertIn('<style id="loop-31654">.elementor-31654 { color: red; }</style>', result)
        self.assertIn('<div class="page-content">Article body here.</div>', result)
        self.assertIn('<div class="elementor-widget-container">', result)

    def test_raises_when_heading_missing(self):
        with self.assertRaises(ValueError):
            replace_related_section("<html><body>no heading here</body></html>", "X")

    def test_raises_when_fewer_than_three_cards(self):
        broken = FIXTURE_PAGE.replace(
            '<div data-elementor-type="loop-item" data-elementor-id="31654" class="old-card-3">\n'
            '            <div class="inner-3">Event card three</div>\n'
            '          </div>\n',
            '',
        )
        with self.assertRaises(ValueError):
            replace_related_section(broken, "X")

    def test_second_run_with_already_new_heading_reshuffles_cards(self):
        already_converted = FIXTURE_PAGE.replace(
            "Other articles that might interest you", "Related blogs"
        )
        result = replace_related_section(already_converted, "SECOND_RUN_CARDS")
        self.assertEqual(result.count("Related blogs"), 1)
        self.assertNotIn("Other articles that might interest you", result)
        self.assertNotIn("old-card-1", result)
        self.assertNotIn("old-card-2", result)
        self.assertNotIn("old-card-3", result)
        self.assertNotIn("News card one", result)
        self.assertEqual(result.count("SECOND_RUN_CARDS"), 1)


if __name__ == "__main__":
    unittest.main()
