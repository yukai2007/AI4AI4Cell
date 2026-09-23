"""Verify a presentation-only rename against its immutable prior commit."""
from pathlib import Path
import hashlib
import json
import subprocess

PAPER=Path(__file__).resolve().parents[1]
BASELINE='2f31454972e01a6da2e5dc27e28ef7be7110f065'

def sha(data):return hashlib.sha256(data).hexdigest()
def previous(path):
    return subprocess.check_output(['git','show',BASELINE+':'+path],cwd=PAPER)

def main():
    unchanged=[]
    for folder in ['tables/strong_v3','tables/core_review','tables/completed_ablation']:
        for path in sorted((PAPER/folder).iterdir()):
            relative=str(path.relative_to(PAPER))
            if path.suffix not in ['.json','.tsv','.tex']:continue
            if relative in ['tables/strong_v3/main.tex','tables/completed_ablation/provenance.json']:continue
            before=previous(relative);after=path.read_bytes()
            if before!=after:raise RuntimeError('Scientific artifact changed: '+relative)
            unchanged.append(dict(path=relative,sha256=sha(after)))
    old=previous('tables/strong_v3/main.tex').decode()
    now=(PAPER/'tables/strong_v3/main.tex').read_text()
    if old.replace('AI4AI4Cell','BioCoLoop')!=now:
        raise RuntimeError('Main table changed beyond framework label')
    sections=[]
    for path in sorted((PAPER/'sections').glob('*.tex')):
        relative=str(path.relative_to(PAPER))
        old=previous(relative).decode().replace('AI4AI4Cell','BioCoLoop')
        old=old.replace('framework_user_20260923_readable_original_labels.pdf','biocoloop_framework.pdf')
        if old!=path.read_text():raise RuntimeError('Section changed beyond allowed rename: '+relative)
        sections.append(relative)
    originals=[]
    for path in [PAPER/'figures/framework_user_20260923_readable_original_labels.pptx',
                 PAPER/'figures/framework_user_20260923_readable_original_labels.pdf',
                 PAPER/'output/pdf/AI4AI4Cell_completed_experiments_20260923.pdf',
                 PAPER/'output/pdf/AI4AI4Cell_中文伴读版.pdf']:
        relative=str(path.relative_to(PAPER))
        if previous(relative)!=path.read_bytes():raise RuntimeError('Historical original overwritten: '+relative)
        originals.append(dict(path=relative,sha256=sha(path.read_bytes())))
    receipt=dict(status='PASS',baseline_commit=BASELINE,framework_name='BioCoLoop',
        scientific_artifacts_unchanged=unchanged,
        main_table_only_framework_label_changed=True,
        sections_only_allowlisted_name_and_asset_changes=sections,
        retained_originals=originals,
        stable_external_identifiers=['repository URL','workspace path','experiment schema','arm ID'])
    out=PAPER/'provenance/rename_biocoloop_20260923/migration_verification.json'
    out.parent.mkdir(exist_ok=True,parents=True)
    stage=out.with_suffix('.json.staging');stage.write_text(json.dumps(receipt,indent=2)+'\n');stage.replace(out)
    print(json.dumps(dict(status='PASS',unchanged_artifacts=len(unchanged),sections=len(sections),
                         historical_originals=len(originals)),indent=2))

if __name__=='__main__':main()
