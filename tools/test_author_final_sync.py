"""Pin the unchanged author PDF and its separately compiled editable source."""
import hashlib
import json
from pathlib import Path
import unittest

from verify_author_final_sync import AUTHOR_SHA, FOLDER
from verify_exact_author_pdf import REBUILD, verify

PAPER = Path(__file__).resolve().parents[1]


class AuthorFinalSyncTests(unittest.TestCase):
    def test_author_reference_is_byte_identical(self):
        self.assertEqual(hashlib.sha256((FOLDER / 'author_submitted.pdf').read_bytes()).hexdigest(), AUTHOR_SHA)

    def test_rebuilt_pages_match_author_without_errata(self):
        result = verify(FOLDER / 'author_submitted.pdf', REBUILD)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['allowed_text_errata'], [])

    def test_canonical_published_pdf_is_byte_identical(self):
        self.assertEqual(hashlib.sha256((PAPER / 'output/pdf/BioCoLoop_manuscript.pdf').read_bytes()).hexdigest(), AUTHOR_SHA)

    def test_scientific_artifact_hashes_are_unchanged(self):
        receipt = json.loads((FOLDER / 'verification.json').read_text())
        self.assertTrue(receipt['scientific_assets_unchanged_from_base'])
        for path, expected in receipt['scientific_asset_sha256'].items():
            self.assertEqual(hashlib.sha256((PAPER / path).read_bytes()).hexdigest(), expected, path)

    def test_chance_mrr_is_the_uniform_five_option_expectation(self):
        self.assertEqual(f'{100 * sum(1 / i for i in range(1, 6)) / 5:.2f}', '45.67')
        appendix = (PAPER / 'sections/22_appendix_unified_protocol.tex').read_text()
        # Preserve the author's submitted text; document its erratum separately.
        self.assertIn('46.00 chance level', appendix)
        record = json.loads((PAPER / 'provenance/author_exact_pdf_20261007/verification.json').read_text())
        self.assertTrue(any('45.67' in issue for issue in record['preserved_reference_issues']))


if __name__ == '__main__':
    unittest.main()
