"""Verify and publish the completed-experiment manuscript without altering results."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import re
import shutil
import fitz

PAPER=Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tests-passed',type=int,required=True)
    p.add_argument('--visual-review',required=True)
    a=p.parse_args()
    assert a.tests_passed>0 and a.visual_review.strip()
    log=(PAPER/'build/main.log').read_text()
    errors=re.findall(r'Overfull[^\n]*|[^\n]*undefined[^\n]*|^!.*',log,re.M)
    if errors: raise RuntimeError(errors)
    provenance=json.loads((PAPER/'tables/completed_ablation/provenance.json').read_text())
    for path,digest in provenance['outputs_sha256'].items():
        path=Path(path)
        target=PAPER.parent/path if path.parts[0]=='paper' else PAPER/path
        if sha(target)!=digest: raise RuntimeError(f'Published artifact changed: {path}')
    snapshot=json.loads((PAPER/'tables/completed_ablation/snapshot.json').read_text())
    pdf=PAPER/'build/main.pdf'
    doc=fitz.open(pdf)
    texts=[page.get_text() for page in doc]
    conclusions=[i+1 for i,t in enumerate(texts) if '6. CONCLUSION' in t]
    statements=[i+1 for i,t in enumerate(texts) if 'REPRODUCIBILITY STATEMENT' in t]
    if len(conclusions)!=1 or len(statements)!=1 or not 1<=conclusions[0]<=statements[0]<=10:
        raise RuntimeError('Check main-text pagination')
    # The statement starts after the conclusion; if it starts on page 10,
    # page 10 must contain only the excluded statements/references.
    if statements[0]>9 and conclusions[0]>=statements[0]:
        raise RuntimeError('Main text exceeds nine-page submission limit')
    joined='\n'.join(texts)
    for forbidden in ('/liziqing/','yukai2007','Kai Yu','Westlake University'):
        if forbidden in joined: raise RuntimeError('Anonymous manuscript: '+forbidden)
    if doc.metadata.get('author') or any(list(p.annots() or []) for p in doc):
        raise RuntimeError('Author metadata or review annotations in submission PDF')
    for required in ('85.47','87.95','35.50','94.60','23.11'):
        if required not in joined: raise RuntimeError('Expected completed evidence absent: '+required)
    files=[PAPER/'main.tex',PAPER/'ai4ai4cell-main.tex',PAPER/'references.bib']
    files+=list((PAPER/'sections').glob('*.tex'))
    files+=list((PAPER/'tables').rglob('*.tex'))
    files+=list((PAPER/'assets').glob('*.pdf'))
    files+=list((PAPER/'figures').glob('*.pdf'))
    for target in [PAPER/'manuscript.pdf',PAPER/'output/pdf/AI4AI4Cell_completed_experiments_20260923.pdf']:
        target.parent.mkdir(parents=True,exist_ok=True)
        stage=target.with_suffix('.pdf.staging')
        shutil.copy2(pdf,stage)
        if sha(stage)!=sha(pdf): raise RuntimeError('PDF copy mismatch')
        stage.replace(target)
    receipt=dict(built_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        manuscript_sha256=sha(pdf),total_pages=len(doc),main_text_ends_page=conclusions[0],
        statements_start_page=statements[0],initial_submission_main_limit=9,
        source_sha256={str(x.relative_to(PAPER)):sha(x) for x in sorted(files)},
        completed_snapshot_sha256=sha(PAPER/'tables/completed_ablation/snapshot.json'),
        publication_provenance_sha256=sha(PAPER/'tables/completed_ablation/provenance.json'),
        unit_tests_passed=a.tests_passed,overfull_boxes=0,undefined_references=0,
        visual_review=a.visual_review,
        incorporated=['five-endpoint two-backend short6','five-endpoint lab count, two definitions',
                      'DTI three independent sources','cell three independent sources',
                      'proteomics two independent sources with matched adapter controls',
                      'four-endpoint long24 curves','504 attempted proposal slots',
                      'user-supplied editable framework figure'],
        unresolved_experimental_scope=['third independent proteomics source not trained',
                                       'native DTI long24 not executed',
                                       'additional ablation seeds deferred'],
        scientific_interpretation='Allocation gains and proposal-history effects are distinct; feedback does not universally improve heldout scores.',
        platform_status='This build does not submit to OpenReview or verify Overleaf remote compilation.')
    out=PAPER/'provenance/completed_ablation_20260923/build_receipt.json'
    stage=out.with_suffix('.json.staging');stage.write_text(json.dumps(receipt,indent=2)+'\n');stage.replace(out)
    print(json.dumps({k:v for k,v in receipt.items() if k!='source_sha256'},indent=2))

if __name__=='__main__':main()
