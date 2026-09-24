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
    p.add_argument('--revision-id',required=True)
    p.add_argument('--revision-description',required=True)
    a=p.parse_args()
    assert a.tests_passed>0 and a.visual_review.strip()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*',a.revision_id):
        raise ValueError('Revision ID must be a simple directory name')
    assert a.revision_description.strip()
    log=(PAPER/'build/main.log').read_text()
    errors=re.findall(r'Overfull[^\n]*|[^\n]*undefined[^\n]*|^!.*',log,re.M)
    if errors: raise RuntimeError(errors)
    provenance=json.loads((PAPER/'tables/completed_ablation/provenance.json').read_text())
    for path,digest in provenance['outputs_sha256'].items():
        path=Path(path)
        target=PAPER.parent/path if path.parts[0]=='paper' else PAPER/path
        if sha(target)!=digest: raise RuntimeError(f'Published artifact changed: {path}')
    snapshot=json.loads((PAPER/'tables/completed_ablation/snapshot.json').read_text())
    protein_path=PAPER.parent/'results/supplemental_20260923/proteomics/seed61_slots0_cpu/independent_rescore.json'
    scenario_path=PAPER.parent/'results/scenario_labs_20260923/heldout/independent_rescore_v2.json'
    protein=json.loads(protein_path.read_text())
    scenario=json.loads(scenario_path.read_text())
    completion_path=scenario_path.parents[1]/'completion_v2.json'
    campaign=json.loads(completion_path.read_text())
    expected_links={
        scenario_path:campaign['independent_rescore_sha256'],
        scenario_path.parent/'results.json':campaign['heldout_results_sha256'],
        scenario_path.parents[1]/'campaign.json':campaign['original_campaign_sha256'],
        scenario_path.parents[1]/'protocol.json':campaign['protocol_sha256'],
    }
    for linked_path,digest in expected_links.items():
        if sha(linked_path)!=digest:
            raise RuntimeError(f'Scenario completion chain mismatch: {linked_path}')
    if campaign['validated_fit_count']!=12 or not campaign['predictions_unchanged']:
        raise RuntimeError('Scenario completion does not validate twelve unchanged predictions')
    if protein['status']!='COMPLETE_VERIFIED' or scenario['status']!='PASS' or campaign['status']!='COMPLETE':
        raise RuntimeError('Supplemental source experiments are not complete and independently verified')
    if len(protein['results'])!=4 or len(scenario['scores'])!=12:
        raise RuntimeError('Incomplete supplemental comparison')
    supplemental_receipts={str(p.relative_to(PAPER.parent)):sha(p) for p in (protein_path,scenario_path,completion_path)}
    strict_dir=PAPER.parent/'results/proteomics_scenario_labs_20260924'
    strict_status=json.loads((strict_dir/'status.json').read_text())
    strict_check=json.loads((strict_dir/'independent_rescore.json').read_text())
    if strict_status['status']!='COMPLETE' or strict_check['status']!='PASS':
        raise RuntimeError('One-study-per-lab proteomics controls are not complete')
    if len(strict_status['completed_arms'])!=4 or strict_status['rounds']!=100 or len(strict_check['results'])!=4:
        raise RuntimeError('Incomplete strict-source proteomics comparison')
    for relative,key in (('protocol.json','protocol_sha256'),('binding.json','binding_sha256'),
                         ('independent_rescore.json','independent_rescore_sha256'),
                         ('heldout/results.json','results_sha256')):
        if sha(strict_dir/relative)!=strict_status[key]:
            raise RuntimeError('Strict-source proteomics receipt mismatch: '+relative)
    for relative in ('status.json','independent_rescore.json'):
        linked=strict_dir/relative
        supplemental_receipts[str(linked.relative_to(PAPER.parent))]=sha(linked)
    pdf=PAPER/'build/main.pdf'
    doc=fitz.open(pdf)
    texts=[page.get_text() for page in doc]
    conclusions=[i+1 for i,t in enumerate(texts) if re.search(r'\b5\.\s*CONCLUSION\b', t)]
    statements=[i+1 for i,t in enumerate(texts) if 'REPRODUCIBILITY STATEMENT' in t]
    if len(conclusions)!=1 or len(statements)!=1 or not 1<=conclusions[0]<=statements[0]<=10:
        raise RuntimeError('Check main-text pagination')
    # The statement starts after the conclusion; if it starts on page 10,
    # page 10 must contain only the excluded statements/references.
    if statements[0]>9 and conclusions[0]>=statements[0]:
        raise RuntimeError('Main text exceeds nine-page submission limit')
    joined='\n'.join(texts)
    if re.search(r'AI4AI4(?:Cell|Bio)',joined,re.I) or 'BioCoLoop' not in joined:
        raise RuntimeError('Framework brand missing or old visible brand remains')
    for forbidden in ('/liziqing/','yukai2007','Kai Yu','Westlake University'):
        if forbidden in joined: raise RuntimeError('Anonymous manuscript: '+forbidden)
    if doc.metadata.get('author') or any(list(p.annots() or []) for p in doc):
        raise RuntimeError('Author metadata or review annotations in submission PDF')
    for required in ('85.47','87.95','35.50','35.68','94.60','23.11','30.70','28.82'):
        if required not in joined: raise RuntimeError('Expected completed evidence absent: '+required)
    statistical_pdf=PAPER/'build/statistical-supplement.pdf'
    statistical_doc=fitz.open(statistical_pdf)
    statistical_text='\n'.join(page.get_text() for page in statistical_doc)
    statistical_log=(PAPER/'build/statistical-supplement.log').read_text()
    statistical_errors=re.findall(r'Overfull[^\n]*|[^\n]*undefined[^\n]*|^!.*',statistical_log,re.M)
    if statistical_errors: raise RuntimeError(statistical_errors)
    for required in ('Table S.1:', 'Table S.2:', 'Unseen protein', 'Norman', 'Tahoe'):
        if required not in statistical_text:
            raise RuntimeError('Statistical supplement missing content: '+required)
    for forbidden in ('/liziqing/','yukai2007','Kai Yu','Westlake University'):
        if forbidden in statistical_text: raise RuntimeError('Anonymous statistical supplement: '+forbidden)
    if statistical_doc.metadata.get('author') or any(list(page.annots() or []) for page in statistical_doc):
        raise RuntimeError('Author metadata or review annotations in statistical supplement')
    statistical_target=PAPER/'output/pdf/BioCoLoop_statistical_supplement.pdf'
    statistical_target.parent.mkdir(parents=True,exist_ok=True)
    stage=statistical_target.with_suffix('.pdf.staging')
    shutil.copy2(statistical_pdf,stage)
    if sha(stage)!=sha(statistical_pdf): raise RuntimeError('Statistical PDF copy mismatch')
    stage.replace(statistical_target)
    statistical_receipt=dict(path=str(statistical_target.relative_to(PAPER)),
        sha256=sha(statistical_pdf),pages=len(statistical_doc),
        source_sha256=sha(PAPER/'statistical-supplement.tex'),
        tables_sha256={name:sha(PAPER/name) for name in
            ('tables/strong_v3/uncertainty.tex','tables/strong_v3/dti_uncertainty.tex')},
        all_contrasts_and_seeds_retained=True,overfull_boxes=0,undefined_references=0,
        submission_instruction='Upload alongside the manuscript as anonymous supplementary material.')
    files=[PAPER/'main.tex',PAPER/'biocoloop-main.tex',PAPER/'statistical-supplement.tex',
           PAPER/'references.bib',PAPER/'references_v2.bib']
    files+=list((PAPER/'sections').glob('*.tex'))
    files+=list((PAPER/'tables').rglob('*.tex'))
    files+=list((PAPER/'assets').glob('*.pdf'))
    files+=list((PAPER/'figures').glob('*.pdf'))
    for target in [PAPER/'manuscript.pdf',PAPER/'output/pdf/BioCoLoop_manuscript.pdf']:
        target.parent.mkdir(parents=True,exist_ok=True)
        stage=target.with_suffix('.pdf.staging')
        shutil.copy2(pdf,stage)
        if sha(stage)!=sha(pdf): raise RuntimeError('PDF copy mismatch')
        stage.replace(target)
    receipt=dict(framework_name='BioCoLoop',revision_id=a.revision_id,
        revision_description=a.revision_description,
        branding_migration_record_sha256=sha(PAPER/'provenance/rename_biocoloop_20260923/migration_verification.json'),
        built_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        manuscript_sha256=sha(pdf),total_pages=len(doc),main_text_ends_page=conclusions[0],
        statements_start_page=statements[0],initial_submission_main_limit=9,
        source_sha256={str(x.relative_to(PAPER)):sha(x) for x in sorted(files)},
        completed_snapshot_sha256=sha(PAPER/'tables/completed_ablation/snapshot.json'),
        publication_provenance_sha256=sha(PAPER/'tables/completed_ablation/provenance.json'),
        supplemental_receipts_sha256=supplemental_receipts,statistical_supplement=statistical_receipt,
        unit_tests_passed=a.tests_passed,overfull_boxes=0,undefined_references=0,
        visual_review=a.visual_review,
        incorporated=['five-endpoint two-backend short6','five-endpoint lab count, two definitions',
                      'DTI three independent sources','cell three independent sources',
                      'proteomics two-source loop study and independent three-source fixed-design extension',
                      'four-endpoint long24 curves','504 attempted proposal slots',
                      'native-vector editable framework figure, explicit inner/outer data flow',
                      'matched K4/N60 source-as-scenario cell comparison',
                      'proteomics one study per training laboratory with target-only development selection'],
        unresolved_experimental_scope=['native DTI long24 not executed',
                                       'proposal-history ablation on the new matched scenario partition not executed',
                                       'additional ablation seeds deferred'],
        scientific_interpretation='Controlled comparisons support collaborative access and trajectory-guided training allocation. Proposal-history effects and source compatibility are evaluated separately; the main table does not combine allocation and proposal revision.',
        platform_status='This build does not submit to OpenReview or verify Overleaf remote compilation.')
    out=PAPER/'provenance'/a.revision_id/'build_receipt.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    stage=out.with_suffix('.json.staging');stage.write_text(json.dumps(receipt,indent=2)+'\n');stage.replace(out)
    print(json.dumps({k:v for k,v in receipt.items() if k!='source_sha256'},indent=2))

if __name__=='__main__':main()
