"""Shorten presentation without selecting experiments by outcome."""
from itertools import product
import hashlib
import json
from pathlib import Path
import re
from statistics import mean
import unittest

PAPER = Path(__file__).resolve().parents[1]


class AppendixCompactionTests(unittest.TestCase):
    def test_complete_uncertainty_tables_move_without_numeric_edits(self):
        original = json.loads((PAPER / 'provenance/terminology_clarity_20260924/build_receipt.json').read_text())
        appendix = (PAPER / 'sections/22_appendix_unified_protocol.tex').read_text()
        supplement = (PAPER / 'statistical-supplement.tex').read_text()
        for name, count, pattern in (
            ('uncertainty', 90, r'^(?:DTI|Proteomics|VCC|Norman|Tahoe) &'),
            ('dti_uncertainty', 72, r'^(?:Random|Unseen drug|Unseen protein) /'),
        ):
            path = f'tables/strong_v3/{name}.tex'
            content = (PAPER / path).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), original['source_sha256'][path])
            self.assertEqual(len(re.findall(pattern, content.decode(), re.M)), count)
            inclusion = r'\input{tables/strong_v3/' + name + '}'
            self.assertIn(inclusion, supplement)
            self.assertNotIn(inclusion, appendix)
        self.assertIn('Tables S.1--S.2', appendix)
        self.assertIn('including zero and negative differences', appendix)
        self.assertIn('in several cell comparisons they include zero', appendix)

    def test_compact_design_mapping_recovers_all_original_configurations(self):
        original = (PAPER / 'tables/completed_ablation/menu_long24.tex').read_text()
        actual = {}
        for line in original.splitlines():
            if not re.match(r'^L\dW\dM\dR\d &', line):
                continue
            fields = [x.strip() for x in line.rstrip('\\ ').split('&')]
            actual[fields[0]] = tuple(float(x) for x in fields[1:4]) + (fields[4] == 'Yes',)
        expected = {
            f'L{i}W{j}M{k}R{l}': ((.0001, .001, .01)[i], (0, .001, .01)[j], (0, .9)[k], bool(l))
            for i, j, k, l in product(range(3), range(3), range(2), range(2))
        }
        self.assertEqual(actual, expected)
        appendix = (PAPER / 'sections/23_appendix_core_sensitivity.tex').read_text()
        self.assertIn('D00--D11 configurations listed in Appendix A.2', appendix)
        for row in (
            r'Learning rate & \texttt{L} & $10^{-4}$ & $10^{-3}$ & $10^{-2}$',
            r'Weight decay & \texttt{W} & $0$ & $10^{-3}$ & $10^{-2}$',
            r'Coordinator momentum & \texttt{M} & $0$ & $0.9$ & --',
            r'Residual module & \texttt{R} & disabled & enabled & --',
        ):
            self.assertIn(row, appendix)
        for name in ('menu_short6', 'menu_long24'):
            self.assertNotIn(r'\input{tables/completed_ablation/' + name + '}', appendix)
            self.assertTrue((PAPER / f'tables/completed_ablation/{name}.tex').is_file())

    def test_core_controls_and_nonpositive_findings_stay_in_manuscript(self):
        appendix_a = (PAPER / 'sections/22_appendix_unified_protocol.tex').read_text()
        for name in ('ablation', 'loop_prefix', 'secondary', 'dti_endpoints'):
            self.assertIn(r'\input{tables/strong_v3/' + name + '}', appendix_a)
        appendix_b = (PAPER / 'sections/23_appendix_core_sensitivity.tex').read_text()
        for name in ('lab_participation', 'lab_fixed_pool', 'transfer_independent',
                     'transfer_protein_loop', 'transfer_contexts', 'short6', 'long24'):
            self.assertIn(r'\input{tables/completed_ablation/' + name + '}', appendix_b)
        results = (PAPER / 'sections/05_results.tex').read_text()
        for phrase in ('retain the same checkpoint', 'eight pairs tie',
                       '28.82', '30.70', '37.07', '25.87'):
            self.assertIn(phrase, results)
        # The non-positive terminal contrast may sit in the main text or in
        # Appendix B; either way it must remain visible in the manuscript.
        self.assertIn('seven ties and one decrease', results + appendix_b)
        scope = (PAPER / 'sections/22_appendix_unified_protocol.tex').read_text()
        self.assertIn(r'\subsection*{A.6 Scope and limitations}', scope)
        self.assertIn('no measurable held-out effect under the fixed proposal budget', scope)

    def test_conclusion_separates_design_search_from_allocation(self):
        snapshot = json.loads((PAPER / 'tables/strong_v3/snapshot.json').read_text())
        conclusion = (PAPER / 'sections/07_conclusion.tex').read_text()
        for task, expected in (('native_tapb', '1.96'), ('norman_double_corrected', '6.77')):
            records = snapshot['tasks'][task]['runs'].values()
            gain = 100 * mean(run['scores']['federated_loop']['primary'] -
                              run['scores']['federated_fixed']['primary'] for run in records)
            self.assertEqual(f'{gain:.2f}', expected)
            self.assertIn(expected, conclusion)
        self.assertIn('over the collaborative default', conclusion)
        self.assertIn('evidence-guided allocation', conclusion)
        self.assertIn('little headroom above the 20', conclusion)


if __name__ == '__main__':
    unittest.main()
