"""Guard the new presentation name without rewriting experiment identities."""
from pathlib import Path
import hashlib
import importlib
import json
import re
import subprocess
import sys
import unittest
import fitz

sys.path.insert(0,str(Path(__file__).resolve().parent))

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
        revisions=json.loads((PAPER/'provenance/coauthor_review_v2_20260923/caption_changes.json').read_text())
        self.assertEqual(revisions['status'], 'CAPTION_ONLY_VERIFIED')
        self.assertEqual(set(revisions['files']), {'tables/completed_ablation/transfer_independent.tex',
                                                  'tables/strong_v3/effects.tex'})
        edits=json.loads((PAPER/'provenance/presentation_edits_20260926/edits.json').read_text())
        self.assertEqual(edits['status'],'PRESENTATION_ONLY_VERIFIED')
        baseline=json.loads((PAPER/'provenance/presentation_edits_20260926/baseline.json').read_text())['commit']
        for path,change in edits['files'].items():
            before=subprocess.check_output(['git','show',f'{baseline}:{path}'],cwd=PAPER)
            after=(PAPER/path).read_bytes()
            self.assertEqual(hashlib.sha256(before).hexdigest(),change['before_sha256'])
            self.assertEqual(hashlib.sha256(after).hexdigest(),change['after_sha256'])
            recorder=importlib.import_module('record_presentation_edits')
            if path==recorder.COLUMN_REMOVED:
                self.assertEqual(recorder.retired_column_body(before),recorder.retired_column_body(after))
            else:
                self.assertEqual(recorder.caption_body(before),recorder.caption_body(after))
        for record in report['scientific_artifacts_unchanged']+report['retained_originals']:
            data=(PAPER/record['path']).read_bytes()
            actual=hashlib.sha256(data).hexdigest()
            if record['path'] in edits['files']:
                self.assertEqual(actual,edits['files'][record['path']]['after_sha256'])
                continue
            if record['path'] in revisions['files']:
                change=revisions['files'][record['path']]
                self.assertEqual(change['before_sha256'],record['sha256'])
                self.assertEqual(actual,change['after_sha256'])
                body=b"".join(line for line in data.splitlines(keepends=True)
                              if not line.startswith(b"\\caption{")).rstrip(b"\n")+b"\n"
                self.assertEqual(hashlib.sha256(body).hexdigest(),change['unchanged_noncaption_sha256'])
            else:
                self.assertEqual(actual,record['sha256'])
        self.assertTrue(report['main_table_only_framework_label_changed'])

    def test_figures_and_chinese_use_current_brand(self):
        for relative in ['assets/paradigm_comparison_v3.pdf','figures/biocoloop_framework_v3.pdf',
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
