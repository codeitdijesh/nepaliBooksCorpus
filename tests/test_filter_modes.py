import unittest

from epustakalaya_corpus.pipeline import manifest_filter_decision


class FilterModeTests(unittest.TestCase):
    def test_exclude_english_textbooks_only_keeps_english_novel(self) -> None:
        row = {
            "title": "Example Novel",
            "language": "English",
            "publisher": "Example Press",
            "keywords": ["Novel", "Literature"],
            "metadata": {},
        }
        keep, reasons = manifest_filter_decision(
            row,
            exclude_english_textbooks_only=True,
        )
        self.assertTrue(keep)
        self.assertEqual(reasons, [])

    def test_exclude_english_textbooks_only_drops_english_textbook(self) -> None:
        row = {
            "title": "Example Science Textbook",
            "language": "English",
            "publisher": "CDC",
            "keywords": ["Textbook", "Grade 10"],
            "metadata": {},
        }
        keep, reasons = manifest_filter_decision(
            row,
            exclude_english_textbooks_only=True,
        )
        self.assertFalse(keep)
        self.assertIn("english_textbook", reasons)


if __name__ == "__main__":
    unittest.main()
