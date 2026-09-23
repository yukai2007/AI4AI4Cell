"""Check that completed evidence is actually linked into the active manuscript."""
from pathlib import Path
import hashlib
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CompletedManuscriptTests(unittest.TestCase):
    def test_active_appendix_uses_completed_not_historical_snapshot(self):
        text=(ROOT/'sections/23_appendix_core_sensitivity.tex').read_text()
        for name in ('lab_participation','lab_fixed_pool','transfer_independent',
                     'transfer_protein_loop','short6','long24','dynamics_long24',
                     'norman_retained_events','trace_short6','trace_long24'):
            self.assertIn(r'\input{tables/completed_ablation/'+name+'}',text)
        self.assertNotIn(r'\input{tables/core_review/',text)
        self.assertNotRegex(text, r'active DTI queue|unfinished study is N/A')

    def test_scope_and_adapter_are_explicit(self):
        text=(ROOT/'sections/23_appendix_core_sensitivity.tex').read_text()
        for phrase in ('two independent external studies','source-specific prediction heads',
                       'not part of this extended protocol','DTI seed 42',
                       '100 training rounds','504'):
            self.assertIn(phrase,text)
        self.assertIn('12-design',text)
        self.assertIn('36-design',text)

    def test_main_result_narrative_links_actual_table(self):
        text=(ROOT/'sections/05_results.tex').read_text()
        self.assertIn(r'\ref{tab:completed-short-summary}',text)
        self.assertIn(r'\input{tables/completed_ablation/summary}',text)
        self.assertIn('other eight paired endpoints tie',text)
        self.assertIn('seven ties and one decrease',text)
        self.assertIn('800 full-client', (ROOT/'tables/strong_v3/effects.tex').read_text())

    def test_actual_framework_asset_is_the_user_slide_derivative(self):
        stem='framework_user_20260923_readable_original_labels'
        method=(ROOT/'sections/03_method.tex').read_text()
        self.assertIn('figures/'+stem+'.pdf',method)
        self.assertNotIn('assets/unified_pipeline.pdf',method)
        receipt=json.loads((ROOT/'figures'/f'{stem}.provenance.json').read_text())
        self.assertEqual(receipt['source_sha256'],
                         'f708424b3f30ed6f7813d66eeddc86e8adf58940091ac1a672703cf267028f81')
        self.assertTrue(receipt['source_unchanged'])
        self.assertTrue(receipt['source_text_identical'])
        for extension,key in [('pdf','vector_pdf_sha256'),('pptx','derived_pptx_sha256')]:
            actual=hashlib.sha256((ROOT/'figures'/f'{stem}.{extension}').read_bytes()).hexdigest()
            self.assertEqual(actual,receipt[key])


if __name__=='__main__':
    unittest.main()
