import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from blog_related_lib import clean_title, extract_post_data


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


if __name__ == "__main__":
    unittest.main()
