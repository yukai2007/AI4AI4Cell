"""Pin the author-selected final manuscript and the explicitly declared errata."""
import hashlib
import json
from pathlib import Path
import unittest

from verify_author_final_sync import AUTHOR_SHA, FOLDER, verify

PAPER = Path(__file__).resolve().parents[1]


class AuthorFinalSyncTests(unittest.TestCase):
    def test_author_reference_is_byte_identical(self):
        self.assertEqual(hashlib.sha256((FOLDER / 'author_submitted.pdf').read_bytes()).hexdigest(), AUTHOR_SHA)

    def test_entire_published_pdf_matches_author_with_declared_errata(self):
        result = verify(FOLDER / 'author_submitted.pdf', PAPER / 'output/pdf/BioCoLoop_manuscript.pdf')
        self.assertEqual(result['status'], 'PASS')

    def test_scientific_artifact_hashes_are_unchanged(self):
        receipt = json.loads((FOLDER / 'verification.json').read_text())
        self.assertTrue(receipt['scientific_assets_unchanged_from_base'])
        for path, expected in receipt['scientific_asset_sha256'].items():
            self.assertEqual(hashlib.sha256((PAPER / path).read_bytes()).hexdigest(), expected, path)

    def test_chance_mrr_is_the_uniform_five_option_expectation(self):
        self.assertEqual(f'{100 * sum(1 / i for i in range(1, 6)) / 5:.2f}', '45.67')
        appendix = (PAPER / 'sections/22_appendix_unified_protocol.tex').read_text()
        self.assertIn('45.67 chance level', appendix)


if __name__ == '__main__':
    unittest.main()
