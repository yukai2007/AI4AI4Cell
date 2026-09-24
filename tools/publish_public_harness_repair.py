"""Read-only, separately labeled transport-repair results (never a v6 overwrite)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

import publish_public_harness as original

TASKS = ('ptpc_neural', 'vcc_corrected', 'norman_double_corrected', 'tahoe_drug_corrected')
NAMES = ('Proteomics AP', 'VCC Top-1', 'Norman Top-1', 'Tahoe Top-1')
VERSION = 'airesearcher-task-transport-compact-v1'
FILES = ('compact_repair_seed42.tex', 'snapshot_compact_repair.json')


def collect(base):
    base = Path(base).resolve()
    manifest_path = base/'queue_manifest.json'
    if not manifest_path.exists():
        return dict(registered=False, resolved=False, scored=0, tasks={})
    manifest = original.read(manifest_path)
    sys.path.insert(0, str(original.EXTENSION))
    from supervise_compact_repair import source_pins
    expected = {('ai_researcher', task, 42) for task in TASKS}
    registered = [(j['harness'], j['task'], j['seed']) for j in manifest['jobs']]
    if (manifest['schema']!='public-harness-compact-repair-queue-v1'
            or len(registered)!=4 or set(registered)!=expected
            or manifest['source_sha256']!=source_pins()
            or manifest['max_gpu_hours']!=2. or manifest['fitting_gpus']!=[0]):
        raise ValueError('Repair registration changed')
    snapshot = original.collect(base)  # Includes independent reconstruction/rescoring.
    result = dict(schema='public-harness-compact-repair-publication-v1',registered=True,
        adapter_version=VERSION,seed=42,base=str(base),manifest_sha256=original.sha(manifest_path),
        source_sha256=manifest['source_sha256'],tasks={},scored=0,resolved=True,
        replaces_original_failures=False,scientific_verification='unchanged full public-harness verifier')
    for task in TASKS:
        run = base/'ai_researcher'/task/'seed42'
        path = run/'run_status.json'
        status = original.read(path) if path.exists() else {}
        measured = snapshot['tasks'][task]['public_harnesses']['ai_researcher']['runs']['42']
        if measured is not None:
            if status.get('transport_revision')!=VERSION or status.get('status')!='DEVELOPMENT_COMPLETE':
                raise ValueError('Scored repair has no matching completed transport revision')
            expected_adapter=original.EXTENSION/'airesearcher_compact.py'
            if str(expected_adapter) not in measured['adapter_paths']:
                raise ValueError('Measured repair did not execute the registered compact adapter')
            result['scored']+=1
            item=dict(status='Scored',primary=measured['primary'],receipt=measured)
        elif status.get('status')=='FAILED':
            item=dict(status='Failed',primary=None,error=status.get('error'),
                      run_status_sha256=original.sha(path))
        else:
            result['resolved']=False
            item=dict(status='Pending',primary=None)
        item['biocoloop_seed42']=snapshot['tasks'][task]['original']['federated_loop']['runs']['42']['primary']
        result['tasks'][task]=item
    return result


def table(snapshot):
    if not snapshot['registered']: return '% No registered compact-repair study.\n'
    def cell(task, reference=False):
        row=snapshot['tasks'][task]
        if not reference and row['status']!='Scored': return row['status']
        value=100*row['biocoloop_seed42'] if reference else 100*row['primary']
        other=(row['primary'] if reference else row['biocoloop_seed42'])
        text=f'{value:.2f}'
        if other is not None and round(value,2)>=round(100*other,2):
            text=r'\textbf{'+text+'}'
        return text
    return '\n'.join([
        r'\begin{table}[t]',r'\centering\footnotesize',r'\setlength{\tabcolsep}{4pt}',
        r'\begin{tabularx}{\linewidth}{@{}Xrrrr@{}}',r'\toprule',
        'Method / transport & '+' & '.join(NAMES)+r' \\',r'\midrule',
        'AI-Researcher / repaired & '+' & '.join(cell(t) for t in TASKS)+r' \\',
        'BioCoLoop & '+' & '.join(cell(t,True) for t in TASKS)+r' \\',r'\bottomrule',r'\end{tabularx}',
        r'\caption{Separate transport-repair study, seed 42, ten laboratories. AI-Researcher uses deduplicated task prompts and an additional unambiguous argument-envelope alias. All scientific budgets and scoring rules remain unchanged. Values are multiplied by 100; bold marks the better value or a tie among scored pairs. Original-adapter failures remain in the preceding comparison.}',
        r'\label{tab:public-harness-compact-repair}',r'\end{table}',''])


def write(base, output):
    snapshot=collect(base)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/FILES[0]).write_text(table(snapshot))
    (output/FILES[1]).write_text(json.dumps(snapshot,indent=2,sort_keys=True)+'\n')
    return snapshot


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();snapshot=write(args.base,args.output_dir)
    print(json.dumps({k:snapshot[k] for k in ('registered','resolved','scored')}))
