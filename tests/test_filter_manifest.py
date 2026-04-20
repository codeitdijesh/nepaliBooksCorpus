import unittest

from epustakalaya_corpus.pipeline import build_manifest_search_blob, manifest_filter_decision


class FilterManifestTests(unittest.TestCase):
    def test_manifest_filter_excludes_english_textbook(self) -> None:
        row = {
            "title": "Computer Science - Grade 10",
            "language": "English",
            "publisher": "CDC",
            "keywords": ["Textbook", "Grade 10"],
            "metadata": {"Education Level": "Secondary"},
        }
        keep, reasons = manifest_filter_decision(
            row,
            exclude_english=True,
            exclude_textbooks=True,
            include_literature=True,
        )
        self.assertFalse(keep)
        self.assertIn("english", reasons)
        self.assertIn("textbook", reasons)

    def test_manifest_filter_keeps_nepali_novel(self) -> None:
        row = {
            "title": "सुम्निमा (उपन्यास)",
            "language": "नेपाली",
            "publisher": "साझा प्रकाशन",
            "keywords": ["Novel", "नेपाली साहित्य", "उपन्यास"],
            "metadata": {"Author(s)": ["बीपी कोइराला"]},
        }
        keep, reasons = manifest_filter_decision(
            row,
            exclude_english=True,
            exclude_textbooks=True,
            include_literature=True,
        )
        self.assertTrue(keep)
        self.assertEqual(reasons, [])

    def test_manifest_search_blob_includes_metadata_values(self) -> None:
        row = {
            "title": "छन्दका १०१ कविता",
            "language": "नेपाली",
            "publisher": None,
            "keywords": ["कविता"],
            "metadata": {"Author(s)": ["कमल दीक्षित"], "Series": "Rato Bangala Kitab"},
        }
        blob = build_manifest_search_blob(row)
        self.assertIn("छन्दका १०१ कविता", blob)
        self.assertIn("कविता", blob)
        self.assertIn("कमल दीक्षित", blob)
        self.assertIn("Series", blob)


if __name__ == "__main__":
    unittest.main()
