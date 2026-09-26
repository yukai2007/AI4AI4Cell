"""Record caption placement and one redundant-column removal as presentation-only edits.

Every listed change is re-derived from the declared baseline commit and re-checked:
caption and label lines may move, and the retired Norman design-id column may be
dropped, but no numeric cell and no executed configuration may change value.
"""
from pathlib import Path
import hashlib
import json
import subprocess

PAPER = Path(__file__).resolve().parents[1]
BASELINE_FILE = PAPER / 'provenance/presentation_edits_20260926/baseline.json'
OUT = PAPER / 'provenance/presentation_edits_20260926/edits.json'
MIGRATION = PAPER / 'provenance/rename_biocoloop_20260923/migration_verification.json'
COLUMN_REMOVED = 'tables/completed_ablation/norman_retained_events.tex'
CAPTION_PREFIXES = (b'\\caption{', b'\\label{')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def caption_body(data):
    lines = [line for line in data.splitlines() if not line.startswith(CAPTION_PREFIXES)]
    return b'\n'.join(lines).rstrip(b'\n') + b'\n'


def retired_column_body(data):
    """Drop the retired Design column so the remaining columns can be compared."""
    rows = []
    for line in data.decode().splitlines():
        if line.startswith('\\begin{tabularx}'):
            rows.append('\\begin{tabularx}')
            continue
        if not line.startswith(('\\caption{', '\\label{')):
            if '&' not in line:
                rows.append(line)
                continue
            fields = [x.strip() for x in line.rstrip('\\ ').split('&')]
            if fields[0] == 'Mode':
                fields = ['Mode', 'Slot', 'Executed configuration', 'Dev. Top-1']
            elif len(fields) == 5:
                fields = [fields[0], fields[1],
                          fields[3].replace('Common initial design', 'Common initial recipe'),
                          fields[4]]
            rows.append(' & '.join(fields))
    return '\n'.join(rows) + '\n'


def previous(path):
    commit = json.loads(BASELINE_FILE.read_text())['commit']
    return subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=PAPER)


def main():
    baseline = json.loads(BASELINE_FILE.read_text())['commit']
    report = json.loads(MIGRATION.read_text())
    records = report['scientific_artifacts_unchanged'] + report['retained_originals']
    files = {}
    for record in records:
        path = record['path']
        target = PAPER / path
        if not target.exists():
            continue
        after = target.read_bytes()
        if sha(after) == record['sha256']:
            continue
        before = previous(path)
        if path == COLUMN_REMOVED:
            assert retired_column_body(before) == retired_column_body(after), path
            kind = 'retired-redundant-design-column'
            reason = ('Design ids such as L0W1M0R0 duplicate the executed '
                      'configuration printed beside them, so the id column was dropped.')
        else:
            assert caption_body(before) == caption_body(after), path
            kind = 'caption-above'
            reason = 'Caption and label moved above the tabular body; no cell changed.'
        files[path] = dict(before_sha256=sha(before), after_sha256=sha(after),
                           kind=kind, reason=reason)
    assert files, 'no presentation edit detected'
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(status='PRESENTATION_ONLY_VERIFIED', baseline_commit=baseline,
                                   files=files), indent=2) + '\n')
    print(json.dumps(dict(status='PRESENTATION_ONLY_VERIFIED', files=len(files),
                          baseline=baseline), indent=2))


if __name__ == '__main__':
    main()
