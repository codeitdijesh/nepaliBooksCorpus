import unittest

from epustakalaya_corpus.pipeline import discover_highest_accessible_page


class CrawlPaginationTests(unittest.TestCase):
    def test_discovers_highest_accessible_page_with_binary_search(self) -> None:
        self.assertEqual(
            discover_highest_accessible_page(
                start_page=1,
                end_page=692,
                is_accessible=lambda page: page <= 625,
            ),
            625,
        )

    def test_returns_start_page_when_no_higher_pages_are_accessible(self) -> None:
        self.assertEqual(
            discover_highest_accessible_page(
                start_page=132,
                end_page=692,
                is_accessible=lambda page: page <= 132,
            ),
            132,
        )


if __name__ == "__main__":
    unittest.main()
