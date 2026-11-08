import importlib.util
import math
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class RebuttalPublicationTests(unittest.TestCase):
    def test_access_render_preserves_fifty_score_cells(self):
        pub = module('publish_rebuttal_access_table')
        old, new = pub.SOURCE.read_text(), pub.render(pub.SOURCE.read_text())
        prefixes = ('Fixed model &', 'Direct &', 'AI-Scientist-v2 &',
                    'AI-Researcher &', r'\textbf{BioCoLoop} &')
        original_rows = [l.split(' & ') for l in old.splitlines() if l.startswith(prefixes)]
        new_rows = [l.split(' & ') for l in new.splitlines() if l.startswith(prefixes)]
        self.assertEqual(len(original_rows), 10)
        for before, after in zip(original_rows, new_rows):
            self.assertEqual(before[1:6], after[2:6] + [after[6].removesuffix(r' \\')])
            self.assertEqual(after[1], '10' if 'BioCoLoop' in before[0] else '1')

    def test_complete_aggregate_export_matches_checked_artifacts(self):
        pub = module('publish_rebuttal_evidence')
        for name, value in pub.export().items():
            self.assertEqual((pub.OUT / name).read_text(), value)

    def test_replies_address_all_three_reviewers(self):
        root = HERE.parent / 'provenance/rebuttal_20261109'
        for name in ('FBhK', 'AfJB', 'cR5g'):
            text = (root / f'RESPONSE_{name}.md').read_text()
            self.assertIn('ten', text)
            self.assertIn('random', text.lower())
            self.assertNotIn('[TODO', text)
            self.assertNotIn('/liziqing/', text)

    def test_current_manuscript_includes_all_new_studies(self):
        root = HERE.parent
        self.assertIn('sections/26_appendix_rebuttal', (root / 'biocoloop-main.tex').read_text())
        results = (root / 'sections/05_results.tex').read_text()
        self.assertIn('tables/rebuttal_20261109/matched_search_main', results)
        appendix = (root / 'sections/26_appendix_rebuttal.tex').read_text()
        for table in ('matched_search_full', 'validation', 'roster', 'source_history'):
            self.assertIn('tables/rebuttal_20261109/' + table, appendix)


if __name__ == '__main__':
    unittest.main()
