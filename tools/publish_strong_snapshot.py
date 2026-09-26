"""Publish the committed task-reference versions, irrespective of test ranking.

No fallback to DrugBAN, linear PTPC, or uncorrected cell features is permitted.
Only complete, independently verified factorial held-out evaluations are included.
All historically exposed endpoints remain labeled retrospective held-out.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import math
import statistics

from publish_unified_snapshot import ARMS, MAIN_ARMS, CONTRASTS, HELDOUT_ROLE, sha

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parent
SEEDS = [42, 43, 44]
TASKS = [('native_tapb', 'DTI', 'DTI'), ('ptpc_neural', 'Proteomics', 'PTPC'),
         ('vcc_corrected', 'VCC', 'VCC'), ('norman_double_corrected', 'Norman', 'Norman'),
         ('tahoe_drug_corrected', 'Tahoe', 'Tahoe')]
MODELS = {'native_tapb': 'TAPB; random task weights with public frozen features',
          'ptpc_neural': 'ProteinTalks-derived observed-response efficacy head (adapted)',
          'vcc_corrected': 'mask-corrected scDEBART adaptation',
          'norman_double_corrected': 'mask-corrected scDEBART adaptation',
          'tahoe_drug_corrected': 'mask-corrected scDEBART with drug-conditioning adapter'}
# Every published arm table shows the committed design: the fixed and feedback-free direct references
# train or search on a single site, so they appear only at one laboratory, and BioCoLoop appears at one
# and ten laboratories.
DISPLAY_ARMS = [arm for arm in ARMS if arm[0] in
                {'single_fixed', 'single_direct', 'single_loop', 'federated_loop'}]

TAPB_CLUSTER_UNITS = {'random': 'SMILES', 'unseen_drug': 'SMILES', 'unseen_protein': 'Protein'}
TAPB_BOOTSTRAP_CONTRASTS = {
    'loop_vs_fixed_federated': ('Loop $-$ fixed (10 labs)', 'federated_loop', 'federated_fixed'),
    'loop_single': ('Loop $-$ direct (1 lab)', 'single_loop', 'single_direct'),
    'loop_federated': ('Loop $-$ direct (10 labs)', 'federated_loop', 'federated_direct'),
    'federation_fixed': ('10 $-$ 1 labs (fixed)', 'federated_fixed', 'single_fixed'),
    'federation_direct': ('10 $-$ 1 labs (direct)', 'federated_direct', 'single_direct'),
    'federation_loop': ('10 $-$ 1 labs (loop)', 'federated_loop', 'single_loop'),
    'main_harness_vs_fixed': ('Our harness $-$ fixed (1 lab)', 'federated_loop', 'single_fixed'),
    'main_harness_vs_direct': ('Our harness $-$ direct (1 lab)', 'federated_loop', 'single_direct'),
}


def read(path):
    return json.loads(path.read_text())


def result_path(base, task, seed):
    if task == 'ptpc_neural': return base/'heldout_ptpc_neural'/f'seed{seed}'
    return base/'heldout_v3'/task/f'seed{seed}'


def tapb_uncertainty(base, seed, path, result, seal, task='native_tapb'):
    """Read optional post-hoc intervals; never modify the frozen point results."""
    if task not in {'native_tapb', 'native_dti'}:
        raise ValueError('Unknown native DTI uncertainty task')
    target = base/f'uncertainty_{task}_v1'/f'seed{seed}.json'
    if not target.exists():
        return None, None
    data = read(target)
    expected_schema = ('native-tapb-posthoc-uncertainty-v1' if task == 'native_tapb'
                       else 'native-dti-posthoc-uncertainty-v1')
    if (data['schema'] != expected_schema
            or data['task'] != task or data['seed'] != seed
            or data['role'] != HELDOUT_ROLE or data['requested_replicates'] != 1000
            or data['rng_seed'] != 20260918):
        raise ValueError('Different post-hoc TAPB uncertainty protocol')
    for key in ['feedback_to_controller', 'model_fitted', 'prediction_generated', 'original_result_modified']:
        if data[key] is not False:
            raise ValueError('Uncertainty supplement must not change the selected models or evaluation')
    for filename in ['results.json', 'seal.json', 'audit.json', 'verification.json']:
        if data['source_sha256'].get(str(path/filename)) != sha(path/filename):
            raise ValueError('Uncertainty supplement binds different frozen evidence')
    if set(data['endpoints']) != set(TAPB_CLUSTER_UNITS):
        raise ValueError('Uncertainty must retain all three DTI endpoints')
    for endpoint, unit in TAPB_CLUSTER_UNITS.items():
        record = data['endpoints'][endpoint]
        if record['cluster_unit'] != unit or set(record['metrics']) != {'auroc', 'average_precision'}:
            raise ValueError('Uncertainty clustering unit or metric set changed')
        if record['rows'] != seal['endpoints'][endpoint]['rows']:
            raise ValueError('Uncertainty roster size mismatch')
        if data['source_sha256'].get(seal['endpoints'][endpoint]['path']) != seal['endpoints'][endpoint]['expected_sha256']:
            raise ValueError('Uncertainty test-input binding differs')
        for arm, _, _ in ARMS:
            evidence = result['endpoints'][endpoint][arm]
            if data['source_sha256'].get(evidence['predictions']) != evidence['predictions_sha256']:
                raise ValueError('Uncertainty prediction binding differs')
        for metric, intervals in record['metrics'].items():
            if (intervals['requested_replicates'] != 1000 or intervals['rng_seed'] != 20260918
                    or intervals['clusters'] < 2
                    or set(intervals['arms']) != {a for a, _, _ in ARMS}
                    or set(intervals['effects']) != set(TAPB_BOOTSTRAP_CONTRASTS)):
                raise ValueError('Incomplete paired bootstrap evidence')
            expected_valid = 1000 - intervals['skipped_single_class_replicates']
            for section in ['arms', 'effects']:
                for entry in intervals[section].values():
                    low, high = entry['ci95']
                    if (not math.isfinite(low) or not math.isfinite(high) or low > high
                            or entry['valid_replicates'] != expected_valid or not 0 < expected_valid <= 1000):
                        raise ValueError('Invalid bootstrap interval or replicate count')
            for arm, _, _ in ARMS:
                if (not math.isfinite(intervals['arms'][arm]['point'])
                        or abs(intervals['arms'][arm]['point']-result['endpoints'][endpoint][arm]['metrics'][metric]) > 1e-12):
                    raise ValueError('Bootstrap point score differs from frozen evaluation')
            for name, (_, first, second) in TAPB_BOOTSTRAP_CONTRASTS.items():
                effect = intervals['effects'][name]
                expected = (result['endpoints'][endpoint][first]['metrics'][metric]
                            - result['endpoints'][endpoint][second]['metrics'][metric])
                if (effect['arms'] != [first, second] or not math.isfinite(effect['difference'])
                        or abs(effect['difference']-expected) > 1e-12):
                    raise ValueError('Bootstrap contrast differs from frozen evaluation')
    return data, target


def collect(base, seeds=None):
    base = Path(base).resolve()
    seeds = list(SEEDS if seeds is None else seeds)
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError('Expected distinct nonempty repetition seeds')
    policy = ROOT/'docs/model_selection_20260918/MAIN_PROTOCOL_DECISION.md'
    snapshot = dict(snapshot_utc=datetime.now(timezone.utc).isoformat(),
        role=HELDOUT_ROLE, seeds_requested=seeds, model_version_policy=str(policy),
        model_version_policy_sha256=sha(policy), selection_on_heldout=False, tasks={})
    for task, label, _ in TASKS:
        item = dict(label=label, model=MODELS[task], runs={str(s):None for s in seeds}, pending={})
        for seed in seeds:
            path = result_path(base, task, seed)
            files = ['results.json', 'seal.json', 'audit.json', 'verification.json']
            if not all((path/name).is_file() for name in files):
                item['pending'][str(seed)] = 'complete verified factorial evaluation not available'; continue
            result, seal, audit, verification = [read(path/name) for name in files]
            if not all(arm in result.get('results', {}) for arm, _, _ in ARMS):
                item['pending'][str(seed)] = 'at least one factorial arm incomplete'; continue
            expected_schema = 'native-tapb-v3-heldout-results-v1' if task == 'native_tapb' else 'unified-v3-heldout-results-v1'
            if result['schema'] != expected_schema:
                raise ValueError('Unknown result schema')
            if not result['task'] == seal['task'] == verification['task'] == task:
                raise ValueError('Reference-model task mismatch; no cross-version substitution')
            if not result['seed'] == seal['seed'] == verification['seed'] == seed:
                raise ValueError('Mismatched training seed')
            if not result['role'] == seal['role'] == HELDOUT_ROLE:
                raise ValueError('Do not relabel retrospective outcomes as blind confirmation')
            if result['feedback_to_controller'] is not False or seal['feedback_to_controller'] is not False:
                raise ValueError('Held-out feedback must not enter design selection')
            if audit['status'] != 'PASS' or verification['status'] != 'PASS':
                raise ValueError('Evaluation lacks independent verification')
            if task == 'native_tapb':
                for key in ['sealed_before_response_access','common_original_roster','original_scorer']:
                    if verification[key] is not True: raise ValueError(f'Missing verification: {key}')
                if verification['arms'] != 6 or verification['endpoints'] != 3:
                    raise ValueError('All six TAPB arms and three endpoints must be independently verified')
                for key in ['development_prediction_parity','fixed_all_three_endpoints','six_arms','original_scorer']:
                    if audit[key] is not True: raise ValueError(f'Missing native invariant: {key}')
                for key in ['test_checkpoint_selection','feedback_to_controller','dictionary_updated']:
                    if audit[key] is not False: raise ValueError('Frozen TAPB evaluation contract changed')
            else:
                for key in ['seal_before_response_access','all_checkpoint_hashes_match','common_original_roster']:
                    if verification[key] is not True: raise ValueError(f'Missing verification: {key}')
                for key in ['original_scorer','common_roster_all_arms','no_test_checkpoint_selection','no_controller_feedback']:
                    if audit[key] is not True: raise ValueError(f'Missing evaluation invariant: {key}')
            if sha(path/'seal.json') != result['seal_sha256']:
                raise ValueError('Changed evaluation seal')
            if not seal['sealed_unix'] <= result['heldout_decoded_unix'] <= result['completed_unix']:
                raise ValueError('Responses were accessed before the selection seal')
            definition = seal['definition']
            if (definition['task'] != task or definition['seed'] != seed or definition['rounds'] != 100
                    or definition['slots'] != 6 or definition['test_read'] is not False):
                raise ValueError('Different protocol cannot enter the uniform main comparison')
            study = base/task/f'study_v3_seed{seed}'
            for filename, key in [('definition.json','definition_sha256'),
                                  ('selected_development.json','selection_sha256')]:
                if sha(study/filename) != seal[key]: raise ValueError('Frozen selection metadata changed')
            if read(study/'status.json')['status'] != 'DEVELOPMENT_COMPLETE':
                raise ValueError('Development study is incomplete')
            version = None
            if task == 'ptpc_neural':
                if seal['predictor'] != MODELS[task] or seal['model_version'] != 'ptpc-observed-6h24h-head-v1':
                    raise ValueError('Expected the registered adapted two-time protein efficacy head')
                registration = study/'neural_registration.json'
                if sha(registration) != seal['registration_sha256']:
                    raise ValueError('Neural adapter binding changed')
                files.append(str(registration))
            elif task.endswith('_corrected'):
                proof = path/'version_proof.json'
                registration_seal = path/'registration_seal.json'
                if not proof.exists() and not registration_seal.exists():
                    item['pending'][str(seed)] = 'corrected-model version receipt not yet available'; continue
                version_path = registration_seal if registration_seal.exists() else proof
                version = read(version_path)
                # Timing/provenance text is retained verbatim. A retrospective
                # integrity receipt is never promoted to a pre-access seal.
                files.append(str(version_path))
                if sha(study/'maskfix_registration.json') != version['registration_sha256']:
                    raise ValueError('Corrected-model registration differs from its version receipt')
                for key in ['selection_sha256','definition_sha256','data_manifest_sha256']:
                    if version[key] != seal[key]: raise ValueError('Model-version receipt binds a different run')
                if version['phase'] == 'PRE_EVALUATION_REGISTRATION_SEAL':
                    if version['verified_unix'] > seal['sealed_unix']:
                        raise ValueError('Registration seal did not precede held-out selection seal')
                elif version['phase'] != 'POSTHOC_INTEGRITY_CHECK':
                    raise ValueError('Unknown model-version receipt timing role')
                for filename,digest in version['source_sha256'].items():
                    if sha(Path(filename)) != digest: raise ValueError('Corrected-model source changed')
                registration = read(study/'maskfix_registration.json')
                if registration['data_manifest_sha256'] != seal['data_manifest_sha256']:
                    raise ValueError('Corrected-feature model identity changed')
                if registration['biological_test_responses_read'] is not False:
                    raise ValueError('Feature preparation consumed biological test responses')
                files.append(str(study/'maskfix_registration.json'))
            elif (seal['source_provenance']['repository'] != 'https://github.com/GaomingL1n/TAPB'
                    or seal['source_provenance']['commit'] != 'ac846b1463ecf4a031b84bd6caacb57b25d50d4f'):
                raise ValueError('DTI main comparison is the pinned TAPB source, never substituted DrugBAN')
            scores = {}
            for arm, _, _ in ARMS:
                value = result['results'][arm]
                primary = value['primary']
                if not math.isfinite(primary): raise ValueError('Non-finite primary score')
                verification_key = f'random/{arm}' if task == 'native_tapb' else arm
                rescored = verification['rescored'][verification_key]['metrics'][result['primary_metric']]
                if abs(primary-rescored) > 1e-12: raise ValueError('Primary independent re-score differs')
                if value['checkpoint'] != seal['arms'][arm]['checkpoint']:
                    reused = value.get('reused_identical_checkpoint')
                    if (task != 'native_tapb' or reused not in seal['arms']
                            or value['checkpoint'] != seal['arms'][reused]['checkpoint']
                            or seal['arms'][arm]['checkpoint_sha256'] != seal['arms'][reused]['checkpoint_sha256']):
                        raise ValueError('Evaluated checkpoint differs from development selection')
                scores[arm] = dict(primary=primary, secondary=value['metrics'])
            endpoints = result.get('endpoints') if task == 'native_tapb' else None
            if task == 'native_tapb':
                if result.get('primary_endpoint') != 'random':
                    raise ValueError('The committed TAPB primary endpoint is random held-out')
                for endpoint in ['random','unseen_drug','unseen_protein']:
                    for arm,_,_ in ARMS:
                        value = endpoints[endpoint][arm]['metrics']['auroc']
                        checked = verification['rescored'][f'{endpoint}/{arm}']['metrics']['auroc']
                        if not math.isfinite(value) or abs(value-checked)>1e-12:
                            raise ValueError('DTI endpoint lacks independent verification')
            supplement = None
            if task == 'native_tapb':
                supplement, supplement_path = tapb_uncertainty(base, seed, path, result, seal)
                if supplement_path is not None:
                    files.append(str(supplement_path))
            receipts = {}
            for filename in files:
                file = Path(filename) if Path(filename).is_absolute() else path/filename
                receipts[str(file.relative_to(base))] = sha(file)
            interval = supplement['endpoints']['random']['metrics']['auroc'] if supplement else result.get('uncertainty')
            item['runs'][str(seed)] = dict(scores=scores, uncertainty=interval,
                primary_metric=result['primary_metric'], receipts=receipts,
                model_version_receipt=version, model=MODELS[task], endpoints=endpoints,
                endpoint_uncertainty=supplement)
        snapshot['tasks'][task] = item
    return snapshot


def runs(snapshot, task):
    return [r for r in snapshot['tasks'][task]['runs'].values() if r is not None]


def stats(values):
    return statistics.mean(values), statistics.stdev(values) if len(values)>1 else None


def scores(snapshot, task, arm, metric=None):
    return [r['scores'][arm]['primary'] if metric is None else r['scores'][arm]['secondary'][metric]
            for r in runs(snapshot, task)]


def table(snapshot, out, full=False):
    arms = DISPLAY_ARMS if full else MAIN_ARMS
    if not full:
        task_order = [task for task, _, _ in TASKS]
        means, deviations = {}, {}
        for arm, _, _ in arms:
            means[arm], deviations[arm] = [], []
            for task in task_order:
                values = scores(snapshot, task, arm)
                mean, sd = stats(values) if values else (None, None)
                means[arm].append(None if mean is None else round(100 * mean, 2))
                deviations[arm].append(None if sd is None else 100 * sd)
        ranks = [sorted({means[arm][j] for arm, _, _ in arms if means[arm][j] is not None},
                        reverse=True) for j in range(len(task_order))]
        def cell(arm, j):
            value = means[arm][j]
            if value is None:
                return 'N/A'
            text = f'{value:.2f}'
            if value == ranks[j][0]:
                text = r'\textbf{' + text + '}'
            elif len(ranks[j]) > 1 and value == ranks[j][1]:
                text = r'\underline{' + text + '}'
            sd = deviations[arm][j]
            return text + r' $\pm$ ' + (f'{sd:.2f}' if sd is not None else 'N/A')
        caption = (r'Main held-out comparison across three task families. Each column uses its named task model in all methods. Direct optimization proposes configurations without evaluation history; BioCoLoop adds collaborative access and evidence feedback. Values are mean $\pm$ sample SD over seeds 42--44, multiplied by 100; SD is not a confidence interval. Bold and underline mark the best and second-best displayed means, including ties. A dash indicates a model for a different task. Full factorial results and secondary metrics are in Appendix A.')
        lines = [r'\begin{table}[t]', r'\caption{' + caption + r'}',
            r'\label{tab:strong-main}',
            r'\centering\footnotesize',
            r'\setlength{\tabcolsep}{3pt}', r'\renewcommand{\arraystretch}{1.12}',
            r'\begin{tabularx}{\linewidth}{@{}Xrrrrr@{}}', r'\toprule',
            r'\textbf{Model / method} & \multicolumn{1}{c}{DTI} & \multicolumn{1}{c}{Proteomics} & \multicolumn{3}{c}{Cell perturbation} \\',
            r'\cmidrule(lr){2-2}\cmidrule(lr){3-3}\cmidrule(l){4-6}',
            r' & \shortstack{BindingDB\\AUROC $\uparrow$} & \shortstack{PTPC\\AP $\uparrow$} & \shortstack{VCC\\Top-1 $\uparrow$} & \shortstack{Norman\\Top-1 $\uparrow$} & \shortstack{Tahoe\\Top-1 $\uparrow$} \\',
            r'\midrule',
            r'\multicolumn{6}{l}{\textit{Fixed task models, one laboratory}} \\']
        for name, columns in [('TAPB', {0}), ('ProteinTalks-derived head', {1}),
                              ('scDEBART response head', {2, 3, 4})]:
            lines.append(name + ' & ' + ' & '.join(cell('single_fixed', j) if j in columns else '--'
                                                  for j in range(5)) + r' \\')
        lines.append(r'\midrule')
        for arm, name in [('single_direct', 'Qwen direct (1 lab)'),
                          ('federated_loop', r'\textbf{BioCoLoop} (10 labs)')]:
            lines.append(name + ' & ' + ' & '.join(cell(arm, j) for j in range(5)) + r' \\')
        lines += [r'\bottomrule', r'\end{tabularx}', r'\end{table}']
        (out/'main.tex').write_text('\n'.join(lines)+'\n')
        return

    caption=('Control comparison for the task-reference models. The fixed and feedback-free direct '
             'references train or search on a single site, so they are reported on one laboratory; '
             'BioCoLoop is reported at one and ten laboratories so that the effect of laboratory '
             'participation can be read under the same research loop. '
             'Entries are held-out mean $\\pm$ sample SD '
             'across completed training/search seeds, multiplied by 100. '
             'The data partitions remain fixed; this SD measures run-to-run variation, not dataset uncertainty. '
             'DTI uses the random held-out endpoint. Bold marks all displayed maxima.')
    label='tab:strong-ablation' if full else 'tab:strong-main'
    lines = [r'\begin{table}[t]',r'\caption{'+caption+'}',r'\label{'+label+'}',
        r'\centering\small',r'\setlength{\tabcolsep}{3pt}',
        r'\begin{tabular}{clrrrrr}',r'\toprule',
        r' & & DTI & Proteomics & \multicolumn{3}{c}{Cell perturbation} \\',r'\cmidrule(lr){5-7}',
        r'Labs & Method & AUROC & AP & VCC & Norman & Tahoe \\',
        r' & & $\uparrow$ & $\uparrow$ & Top-1 $\uparrow$ & Top-1 $\uparrow$ & Top-1 $\uparrow$ \\',r'\midrule']
    for arm,labs,name in arms:
        cells=[]
        for task,_,_ in TASKS:
            values=scores(snapshot,task,arm)
            if not values: cells.append('N/A'); continue
            mean,sd=stats(values); value=round(100*mean,2)
            best=max(round(100*stats(scores(snapshot,task,a))[0],2) for a,_,_ in arms)
            text=f'{value:.2f}'
            if value==best: text=r'\textbf{'+text+'}'
            if full and sd is not None: text+=r'{\scriptsize$\pm'+f'{100*sd:.2f}'+r'$}'
            cells.append(text)
        if labs=='10': lines.append(r'\midrule')
        lines.append(f'{labs} & {name} & '+' & '.join(cells)+r' \\')
    requested = len(snapshot.get('seeds_requested', SEEDS))
    lines += [r'\midrule',r'\multicolumn{2}{l}{Completed seeds ($n/'+str(requested)+r'$)} & '+' & '.join(
        f'{len(runs(snapshot,t))}/{requested}' for t,_,_ in TASKS)+r' \\',r'\bottomrule',r'\end{tabular}',
        r'\end{table}']
    (out/('ablation.tex' if full else 'main.tex')).write_text('\n'.join(lines)+'\n')


def effects(snapshot,out,full=False):
    if not full:
        row_labels = {
            'native_tapb': 'DTI: TAPB random split',
            'ptpc_neural': 'Proteomics: efficacy',
            'vcc_corrected': 'Cell: VCC single-gene',
            'norman_double_corrected': 'Cell: Norman double-gene',
            'tahoe_drug_corrected': 'Cell: Tahoe drug',
        }
        comparisons = [
            ('Search effect', 'federated_loop', 'federated_fixed'),
            ('Feedback effect', 'federated_loop', 'federated_direct'),
            ('Participation effect', 'federated_loop', 'single_loop'),
        ]
        caption = (r'Does early evidence improve training allocation? Held-out scores use the same ten designs, ten laboratories, 800 full-client rounds and 160 aggregate development evaluations per method. Uniform allocation gives every design 80 rounds; the evidence-guided scheduler screens all designs for 20 rounds and restarts six promoted designs for 100-round training. Gain is evidence-guided minus uniform, in percentage points; W/T/L counts seed-level wins, ties and losses (total 4/8/0). Norman 95\% CI: [4.54, 17.73]; Tahoe: [$-$1.00, 7.46]. The separate DTI development replay is in Appendix A.')
        lines = [r'\begin{table}[h!]', r'\caption{' + caption + r'}',
            r'\label{tab:strong-effects}',
            r'\centering\small', r'\setlength{\tabcolsep}{7pt}',
            r'\renewcommand{\arraystretch}{1.08}',
            r'\begin{tabularx}{\linewidth}{@{}Xrrr@{}}', r'\toprule',
            r'\textbf{Benchmark} & \shortstack{Design search\\10 labs} & '
            r'\shortstack{Feedback\\10 labs} & \shortstack{Participation\\loop fixed} \\',
            r'\midrule']
        for task, _, _ in TASKS:
            cells = []
            for _, a, b in comparisons:
                values = [100 * (run['scores'][a]['primary'] - run['scores'][b]['primary'])
                          for run in runs(snapshot, task)]
                cells.append(f'{statistics.mean(values):+.2f}' if values else 'N/A')
            lines.append(row_labels[task] + ' & ' + ' & '.join(cells) + r' \\')
        lines += [r'\bottomrule', r'\end{tabularx}', r'\end{table}']
        (out/'effects.tex').write_text('\n'.join(lines)+'\n')
        return

    caption=('Complete decomposition into design-search improvement (loop minus fixed), feedback-specific improvement (loop minus matched-budget direct), and laboratory-participation improvement (ten minus one lab with loop fixed). Mean paired held-out differences are in percentage points over the three seeds and are computed before rounding.')
    label='tab:strong-effects-full' if full else 'tab:strong-effects'
    lines=[r'\begin{table}[t]',r'\caption{'+caption+'}',r'\label{'+label+'}',
        r'\centering\small',r'\setlength{\tabcolsep}{3pt}',
        r'\begin{tabular}{lrrrrr}',r'\toprule',
        r'Held-out contrast & DTI & Proteomics & VCC & Norman & Tahoe \\',r'\midrule']
    comparisons = [('Loop $-$ fixed (1 lab)','single_loop','single_fixed'),
                   ('Loop $-$ fixed (10 labs)','federated_loop','federated_fixed')]+CONTRASTS
    for label,a,b in comparisons:
        cells=[]
        for task,_,_ in TASKS:
            values=[100*(r['scores'][a]['primary']-r['scores'][b]['primary']) for r in runs(snapshot,task)]
            cells.append(f'{statistics.mean(values):+.2f}' if values else 'N/A')
        lines.append(label+' & '+' & '.join(cells)+r' \\')
    lines += [r'\midrule','Completed seeds ($n/3$) & '+' & '.join(
        f'{len(runs(snapshot,t))}/3' for t,_,_ in TASKS)+r' \\',r'\bottomrule',r'\end{tabular}',
        r'\caption{Complete decomposition into design-search improvement (loop minus fixed), feedback-specific improvement (loop minus matched-budget direct), and laboratory-participation improvement (ten minus one lab with loop fixed). Mean paired held-out differences are in percentage points over the three seeds and are computed before rounding.}',
        r'\label{'+('tab:strong-effects-full' if full else 'tab:strong-effects')+'}',r'\end{table}']
    (out/('effects_full.tex' if full else 'effects.tex')).write_text('\n'.join(lines)+'\n')


def secondary(snapshot,out):
    lines=[r'\begin{longtable}{llrrrr}',
        r'\caption{Held-out secondary metrics for the task-reference models, averaged over seeds 42--44 and multiplied by 100. Bold indicates all tied maxima, or minima for loss.}\label{tab:strong-secondary}\\',
        r'\toprule Method & Labs & Metric 1 & Metric 2 & Metric 3 & Metric 4 \\ \midrule\endfirsthead',
        r'\toprule Method & Labs & Metric 1 & Metric 2 & Metric 3 & Metric 4 \\ \midrule\endhead']
    for task,label,_ in TASKS:
        if task=='native_tapb': keys=['auroc','average_precision','mcc','log_loss']; names=['AUROC','AP','MCC','BCE']
        elif task=='ptpc_neural': keys=['ap','auroc','bce','accuracy_at_0_5']; names=['AP','AUROC','BCE','Acc.']
        else: keys=['accuracy','mrr','top3','cross_entropy']; names=['Micro Top-1','MRR','Top-3','CE']
        lines.append(r'\multicolumn{2}{l}{\textbf{'+label+f' ($n={len(runs(snapshot,task))}$)'+r'}} & '+' & '.join(names)+r' \\')
        for arm,labs,name in DISPLAY_ARMS:
            cells=[]
            for key in keys:
                values=scores(snapshot,task,arm,key)
                if not values: cells.append('N/A'); continue
                value=round(statistics.mean(values),4)
                others=[round(statistics.mean(scores(snapshot,task,a,key)),4) for a,_,_ in DISPLAY_ARMS]
                best=min(others) if key in ['bce','log_loss','cross_entropy'] else max(others)
                text=f'{100*value:.2f}'; cells.append(r'\textbf{'+text+'}' if value==best else text)
            lines.append(f'{name} & {labs} & '+' & '.join(cells)+r' \\')
        lines.append(r'\midrule')
    lines += [r'\bottomrule',r'\end{longtable}']; (out/'secondary.tex').write_text('\n'.join(lines)+'\n')


def uncertainty(snapshot,out):
    lines=[r'\begin{longtable}{llrrl}',
        r'\caption{Paired cluster-bootstrap 95\% intervals for each seed and main contrast, in percentage points. Intervals condition on the selected trained models; DTI random-endpoint rows resample drug clusters.}\label{tab:strong-uncertainty}\\',
        r'\toprule Task & Contrast & Seed & Difference & 95\% interval \\ \midrule\endfirsthead',
        r'\toprule Task & Contrast & Seed & Difference & 95\% interval \\ \midrule\endhead']
    keys=['loop_vs_fixed_federated','loop_single','loop_federated','federation_fixed','federation_direct','federation_loop']
    contrasts=[('Loop $-$ fixed (10 labs)','federated_loop','federated_fixed')]+CONTRASTS
    for task,label,_ in TASKS:
        for seed,run in snapshot['tasks'][task]['runs'].items():
            if run is None: continue
            if run['uncertainty'] is None:
                lines.append(f'{label} & Bootstrap intervals pending & {seed} & N/A & N/A'+r' \\')
                continue
            for (contrast,_,_),key in zip(contrasts,keys):
                effect=run['uncertainty']['effects'][key]; lo,hi=effect['ci95']
                lines.append(f"{label} & {contrast} & {seed} & {100*effect['difference']:+.2f} & [{100*lo:+.2f}, {100*hi:+.2f}]"+r' \\')
            lines.append(r'\midrule')
    lines += [r'\bottomrule',r'\end{longtable}']; (out/'uncertainty.tex').write_text('\n'.join(lines)+'\n')


def dti_uncertainty(snapshot, out, task='native_tapb'):
    if task not in {'native_tapb', 'native_dti'}:
        raise ValueError('Unknown uncertainty table model')
    model = 'TAPB' if task == 'native_tapb' else 'historical DrugBAN'
    table_label = 'tab:strong-dti-uncertainty' if task == 'native_tapb' else 'tab:diagnostic-drugban-uncertainty'
    filename = 'dti_uncertainty.tex' if task == 'native_tapb' else 'drugban_uncertainty.tex'
    lines=[r'\begingroup\scriptsize\setlength{\tabcolsep}{3pt}',
        r'\begin{longtable}{llrrrr}',
        r'\caption{Post-hoc '+model+r' paired AUROC/AP differences and 95\% intervals from 1,000 fixed-seed cluster-bootstrap draws. Random and unseen-drug endpoints use drug clusters; unseen-protein uses protein clusters. All three endpoints and prespecified contrasts are shown.}\label{'+table_label+r'}\\',
        r'\toprule Endpoint / seed & Contrast & AUROC $\Delta$ & 95\% interval & AP $\Delta$ & 95\% interval \\ \midrule\endfirsthead',
        r'\toprule Endpoint / seed & Contrast & AUROC $\Delta$ & 95\% interval & AP $\Delta$ & 95\% interval \\ \midrule\endhead']
    labels={'random':'Random','unseen_drug':'Unseen drug','unseen_protein':'Unseen protein'}
    for seed, run in snapshot['tasks'][task]['runs'].items():
        if run is None: continue
        supplement = run.get('endpoint_uncertainty')
        if supplement is None:
            lines.append(f'All / {seed} & Supplement pending & N/A & N/A & N/A & N/A'+r' \\')
            continue
        for endpoint in TAPB_CLUSTER_UNITS:
            for key, (label, _, _) in TAPB_BOOTSTRAP_CONTRASTS.items():
                cells=[]
                for metric in ['auroc','average_precision']:
                    entry=supplement['endpoints'][endpoint]['metrics'][metric]['effects'][key]
                    low,high=entry['ci95']
                    cells.extend([f"{100*entry['difference']:+.2f}",f'[{100*low:+.2f}, {100*high:+.2f}]'])
                lines.append(f'{labels[endpoint]} / {seed} & {label} & '+' & '.join(cells)+r' \\')
            lines.append(r'\midrule')
    lines += [r'\bottomrule',r'\end{longtable}',r'\endgroup']
    (out/filename).write_text('\n'.join(lines)+'\n')


def macros(snapshot,out):
    lines=['% Generated from verified committed-reference held-out versions only.']
    for task,_,prefix in TASKS:
        current=runs(snapshot,task); values={'Seeds':str(len(current))}
        for suffix,arm in [('Fixed','single_fixed'),('Direct','single_direct'),('Harness','federated_loop')]:
            values[suffix]=f'{100*statistics.mean(scores(snapshot,task,arm)):.2f}' if current else 'N/A'
        for suffix,a,b in [('DeltaDirect','federated_loop','single_direct'),('DeltaFixed','federated_loop','single_fixed'),
                           ('SearchEffect','federated_loop','federated_fixed'),
                           ('SingleSearchEffect','single_loop','single_fixed'),
                           ('LoopEffect','federated_loop','federated_direct'),
                           ('SingleLoopEffect','single_loop','single_direct'),
                           ('FederationEffect','federated_loop','single_loop')]:
            values[suffix]=(f"{100*statistics.mean(r['scores'][a]['primary']-r['scores'][b]['primary'] for r in current):+.2f}" if current else 'N/A')
        values['ThreeSeedHarness']=values['Harness'] if len(current)==3 else 'N/A'
        for suffix,value in values.items(): lines.append(r'\newcommand{\Strong'+prefix+suffix+'}{'+value+'}')
    (out/'snapshot_stats.tex').write_text('\n'.join(lines)+'\n')


def dti_endpoints(snapshot,out):
    current=runs(snapshot,'native_tapb')
    lines=[r'\begin{longtable}{llrrr}',
        r'\caption{All three frozen TAPB held-out endpoints under the committed common protocol. Scores are completed-seed means multiplied by 100; N/A means no complete independently verified evaluation. The main DTI endpoint is random held-out.}\label{tab:strong-dti-endpoints}\\',
        r'\toprule Endpoint & Method & Labs & AUROC & AP \\ \midrule\endfirsthead',
        r'\toprule Endpoint & Method & Labs & AUROC & AP \\ \midrule\endhead']
    for endpoint,label in [('random','Random'),('unseen_drug','Unseen drug'),('unseen_protein','Unseen protein')]:
        for arm,labs,name in DISPLAY_ARMS:
            cells=[]
            for metric in ['auroc','average_precision']:
                if not current: cells.append('N/A'); continue
                means={a:round(100*statistics.mean(r['endpoints'][endpoint][a]['metrics'][metric] for r in current),2) for a,_,_ in DISPLAY_ARMS}
                value=f'{means[arm]:.2f}'; cells.append(r'\textbf{'+value+'}' if means[arm]==max(means.values()) else value)
            lines.append(f'{label} & {name} & {labs} & '+' & '.join(cells)+r' \\')
        lines.append(r'\midrule')
    lines += [r'\bottomrule',r'\end{longtable}']; (out/'dti_endpoints.tex').write_text('\n'.join(lines)+'\n')


def main():
    from publish_racing_snapshot import publish_racing
    parser=argparse.ArgumentParser(); parser.add_argument('--results',type=Path,default=ROOT/'results/unified_bio_20260918')
    args=parser.parse_args(); snapshot=collect(args.results); out=PAPER/'tables/strong_v3'; out.mkdir(parents=True,exist_ok=True)
    (out/'snapshot.json').write_text(json.dumps(snapshot,indent=2,allow_nan=False)+'\n')
    table(snapshot,out); table(snapshot,out,True); publish_racing(args.results,out); effects(snapshot,out,True); secondary(snapshot,out)
    uncertainty(snapshot,out); macros(snapshot,out); dti_endpoints(snapshot,out); dti_uncertainty(snapshot,out)
    print(json.dumps(dict(completed_seeds={t:len(runs(snapshot,t)) for t,_,_ in TASKS},role=HELDOUT_ROLE)))


if __name__=='__main__': main()
