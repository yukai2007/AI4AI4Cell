"""Guard the new presentation name without rewriting experiment identities."""
from pathlib import Path
import hashlib
import json
import re
import unittest
import fitz

PAPER=Path(__file__).resolve().parents[1]

class BrandIdentityTests(unittest.TestCase):
    def test_current_entry_and_text(self):
        self.assertIn(r'\input{biocoloop-main.tex}',(PAPER/'main.tex').read_text())
        self.assertIn(r'\input{biocoloop-main.tex}',(PAPER/'ai4ai4cell-main.tex').read_text())
        source=(PAPER/'biocoloop-main.tex').read_text()
        self.assertIn('BioCoLoop: Collaborative Agentic Research',source)
        for path in [PAPER/'biocoloop-main.tex',*sorted((PAPER/'sections').glob('*.tex')),
                     PAPER/'tables/strong_v3/main.tex']:
            self.assertNotRegex(path.read_text(),r'(?i)AI4AI4(?:Cell|Bio)')

    def test_scientific_artifacts_and_archives_remain_identical(self):
        report=json.loads((PAPER/'provenance/rename_biocoloop_20260923/migration_verification.json').read_text())
        self.assertEqual(report['status'],'PASS')
        for record in report['scientific_artifacts_unchanged']+report['retained_originals']:
            self.assertEqual(hashlib.sha256((PAPER/record['path']).read_bytes()).hexdigest(),record['sha256'])
        self.assertTrue(report['main_table_only_framework_label_changed'])

    def test_figures_and_chinese_use_current_brand(self):
        for relative in ['assets/paradigm_comparison.pdf','figures/biocoloop_framework.pdf',
                         'output/pdf/BioCoLoop_中文伴读版.pdf']:
            with fitz.open(PAPER/relative) as doc:
                text='\n'.join(page.get_text() for page in doc)
                self.assertIn('BioCoLoop',text)
                self.assertNotRegex(text,r'(?i)AI4AI4(?:Cell|Bio)')

    def test_no_dead_repository_rename(self):
        readme=(PAPER/'README.md').read_text()
        self.assertIn('https://github.com/yukai2007/AI4AI4Cell',readme)
        self.assertNotIn('https://github.com/yukai2007/BioCoLoop',readme)
        for file in ['tools/publish_strong_snapshot.py','tools/draw_paradigm_comparison.py',
                     'tools/build_chinese_companion.py']:
            self.assertIn('BioCoLoop',(PAPER/file).read_text())

if __name__=='__main__':unittest.main()
