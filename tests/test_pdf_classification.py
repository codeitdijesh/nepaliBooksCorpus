import unittest
import uuid
from pathlib import Path

import fitz

from epustakalaya_corpus.pipeline import inspect_pdf_text_profile


class PdfClassificationTests(unittest.TestCase):
    def test_native_pdf_is_classified_as_native(self) -> None:
        pdf_path = Path("data") / f"native_{uuid.uuid4().hex}.pdf"
        try:
            document = fitz.open()
            page = document.new_page()
            page.insert_text((72, 72), "This page has enough native text to be classified as native.")
            document.save(pdf_path)
            document.close()

            profile = inspect_pdf_text_profile(pdf_path, min_chars_per_page=20)
            self.assertEqual(profile["text_access"], "native")
            self.assertEqual(profile["ocr_candidate_pages"], 0)
        finally:
            if pdf_path.exists():
                pdf_path.unlink()

    def test_blank_pdf_is_classified_as_ocr(self) -> None:
        pdf_path = Path("data") / f"blank_{uuid.uuid4().hex}.pdf"
        try:
            document = fitz.open()
            document.new_page()
            document.save(pdf_path)
            document.close()

            profile = inspect_pdf_text_profile(pdf_path, min_chars_per_page=20)
            self.assertEqual(profile["text_access"], "ocr")
            self.assertEqual(profile["native_text_pages"], 0)
        finally:
            if pdf_path.exists():
                pdf_path.unlink()

    def test_mixed_pdf_is_classified_as_mixed(self) -> None:
        pdf_path = Path("data") / f"mixed_{uuid.uuid4().hex}.pdf"
        try:
            document = fitz.open()
            text_page = document.new_page()
            text_page.insert_text((72, 72), "This page has enough native text to count.")
            document.new_page()
            document.save(pdf_path)
            document.close()

            profile = inspect_pdf_text_profile(pdf_path, min_chars_per_page=20)
            self.assertEqual(profile["text_access"], "mixed")
            self.assertEqual(profile["pages_total"], 2)
            self.assertEqual(profile["native_text_pages"], 1)
            self.assertEqual(profile["ocr_candidate_pages"], 1)
        finally:
            if pdf_path.exists():
                pdf_path.unlink()


if __name__ == "__main__":
    unittest.main()
