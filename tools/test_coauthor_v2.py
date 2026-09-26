"""Regression checks for coauthor V2 and source-defined lab interpretation."""
from pathlib import Path
import hashlib
import json
import re
import unittest

PAPER=Path(__file__).resolve().parents[1]

class SecondReviewTests(unittest.TestCase):
    def test_all_annotation_anchors_have_a_response(self):
        folder=PAPER/'provenance/coauthor_review_v2_20260923'
        data=json.loads((folder/'annotations.json').read_text())
        rows=data['annotations']
        self.assertEqual(len(rows),27)
        reply=(folder/'RESPONSE.zh-CN.md').read_text()
        for index,row in enumerate(rows,1):
            self.assertIn(f'V2-{index:02d}',reply)
            self.assertIn('x'+str(row['xref']),reply)

    def test_experiments_are_one_section_and_model_names_are_explicit(self):
        design=(PAPER/'sections/04_experimental_design.tex').read_text()
        results=(PAPER/'sections/05_results.tex').read_text()
        self.assertIn(r'\section*{4. Experiments}',design)
        self.assertNotRegex(results,r'\\section\*\{[0-9]+\. Results')
        table=(PAPER/'tables/strong_v3/main.tex').read_text()
        for name in ('TAPB','ProteinTalks-derived head','scDEBART response head'):
            self.assertIn(name,table)
        self.assertNotIn('Overall',table)
        self.assertNotIn('Task model (1 lab)',table)
        self.assertIn('--',table)
        self.assertIn(r'\textbf{25.56}',table)

    def test_main_partition_and_source_studies_are_not_equated(self):
        text=(PAPER/'sections/04_experimental_design.tex').read_text()
        self.assertIn('divided into ten disjoint groups',text)
        self.assertIn('treated as separate laboratories',text)
        self.assertIn('tests whether information can transfer across genuinely different data sources',text)
        appendix=(PAPER/'sections/23_appendix_core_sensitivity.tex').read_text()
        appendix+=(PAPER/'tables/supplemental_20260923/source_client_mapping.tex').read_text()
        self.assertIn('Replogle',appendix)
        self.assertIn('Nadig',appendix)
        self.assertIn('Jiang',appendix)

    def test_laboratory_plot_preserves_all_points(self):
        receipt=json.loads((PAPER/'assets/laboratory_sensitivity_v2.json').read_text())
        path=PAPER/receipt['source']
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),receipt['source_sha256'])
        records=json.loads(path.read_text())['laboratory']
        self.assertEqual(len(receipt['plotted']),10)
        for record in records:
            points=receipt['plotted'][record['task']+'/'+record['family']]
            self.assertEqual(points['k'],[1,2,5,10])
            for index,k in enumerate(points['k']):
                values=[100*v for v in record['by_k'][str(k)]]
                self.assertEqual(points['samples'][index],values)
                self.assertAlmostEqual(points['means'][index],sum(values)/len(values))

    def test_new_sources_do_not_replace_original_numeric_snapshots(self):
        original=json.loads((PAPER/'provenance/rename_biocoloop_20260923/migration_verification.json').read_text())
        for name in ('tables/strong_v3/snapshot.json','tables/completed_ablation/snapshot.json'):
            expected=next(x['sha256'] for x in original['scientific_artifacts_unchanged'] if x['path']==name)
            self.assertEqual(hashlib.sha256((PAPER/name).read_bytes()).hexdigest(),expected)

    def test_method_math_and_section_labels_are_not_duplicated(self):
        text=(PAPER/'sections/03_method.tex').read_text()
        labels=re.findall(r'\\label\{([^}]+)\}',text)
        self.assertEqual(len(labels),len(set(labels)))
        self.assertEqual(text.count(r'\subsection*'),4)
        self.assertIn('3.4 Evidence-guided training allocation',text)
        for line in text.splitlines():
            self.assertEqual(len(re.findall(r'(?<!\\)\$',line)) % 2,0,line)
        self.assertIn('loss on panel $i$. The coordinator computes',text)

if __name__=='__main__':
    unittest.main()
