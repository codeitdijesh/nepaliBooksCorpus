import unittest

from epustakalaya_corpus.parsers import parse_detail_page, parse_search_page
from epustakalaya_corpus.utils import normalize_digits, parse_int


SEARCH_HTML = """
<html>
  <body>
    <a href="/documents/detail/11111111-1111-1111-1111-111111111111/" title="Doc One">Doc One</a>
    <h1><a href="/documents/detail/22222222-2222-2222-2222-222222222222/" tabindex="0">Doc Two</a></h1>
    <a href="?page=1&form-filter=&q=">1</a>
    <a href="?page=12&form-filter=&q=">12</a>
  </body>
</html>
"""


DETAIL_HTML = """
<html>
  <head>
    <title>E-Pustakalaya | Document | Sample Book</title>
  </head>
  <body>
    <p>File size: 3.29 MB</p>
    <span>६१९९ Views,&nbsp;</span>
    <span>&nbsp;0 Reviews</span>
    <a href="/accounts/login?next=/documents/detail/33333333-3333-3333-3333-333333333333/">Log-in</a>
    <table>
      <tr><th>Publisher:</th><td>Sample Publisher</td></tr>
      <tr><th>Publication year:</th><td>वि. सं. २०६२</td></tr>
      <tr><th>Total pages:</th><td>१२३</td></tr>
      <tr><th>Language:</th><td>नेपाली</td></tr>
      <tr><th>Keywords:</th><td><a href="#">बालकविता</a><a href="#">Nepali Poetry</a></td></tr>
    </table>
    <script>
      const pdfUrl = '/media/uploads/op/pdf/sample.pdf/sample.pdf';
      $.ajax({ url: '/documents/increment_download_count/33333333-3333-3333-3333-333333333333/' });
    </script>
    <div>
      Unless explicitly mentioned, all the contents on this website are licensed under
      <a href="https://creativecommons.org/licenses/by-nc-nd/3.0/"><b>Creative Commons</b></a>
    </div>
  </body>
</html>
"""


class ParserTests(unittest.TestCase):
    def test_parse_search_page(self) -> None:
        parsed = parse_search_page(SEARCH_HTML, "https://pustakalaya.org")
        self.assertEqual(parsed["total_pages"], 12)
        self.assertEqual(len(parsed["results"]), 2)
        self.assertEqual(parsed["results"][0]["doc_id"], "11111111-1111-1111-1111-111111111111")

    def test_parse_detail_page(self) -> None:
        parsed = parse_detail_page(
            DETAIL_HTML,
            "https://pustakalaya.org/documents/detail/33333333-3333-3333-3333-333333333333/",
        )
        self.assertEqual(parsed["doc_id"], "33333333-3333-3333-3333-333333333333")
        self.assertEqual(parsed["title"], "Sample Book")
        self.assertEqual(parsed["pdf_url"], "https://pustakalaya.org/media/uploads/op/pdf/sample.pdf/sample.pdf")
        self.assertEqual(
            parsed["download_count_url"],
            "https://pustakalaya.org/documents/increment_download_count/33333333-3333-3333-3333-333333333333/",
        )
        self.assertEqual(parsed["views"], 6199)
        self.assertEqual(parsed["pages_total"], 123)
        self.assertEqual(parsed["language"], "नेपाली")
        self.assertEqual(parsed["keywords"], ["बालकविता", "Nepali Poetry"])

    def test_digit_normalization(self) -> None:
        self.assertEqual(normalize_digits("१२३४५"), "12345")
        self.assertEqual(parse_int("६,१९९ Views"), 6199)


if __name__ == "__main__":
    unittest.main()
