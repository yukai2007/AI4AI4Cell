"""Preserve the new experiment scripts with hashes, without data or checkpoints."""
from pathlib import Path
import hashlib
import json
import zipfile

PAPER = Path(__file__).resolve().parents[1]
PROJECT = PAPER.parent
SOURCE = PROJECT / 'extensions/rebuttal_20261109'
OUT = PAPER / 'provenance/rebuttal_20261109'


def main():
    paths = sorted(SOURCE.rglob('*.py'))
    assert paths and all(p.is_file() and not p.is_symlink() for p in paths)
    archive = OUT / 'experiment_sources.zip'
    records = {}
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in paths:
            name = path.relative_to(PROJECT).as_posix()
            raw = path.read_bytes()
            records[name] = hashlib.sha256(raw).hexdigest()
            entry = zipfile.ZipInfo(name, date_time=(2026, 11, 9, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            bundle.writestr(entry, raw)
    with zipfile.ZipFile(archive) as bundle:
        assert sorted(bundle.namelist()) == sorted(records)
        assert all(hashlib.sha256(bundle.read(name)).hexdigest() == digest
                   for name, digest in records.items())
    manifest = dict(status='PASS', archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        source_sha256=records, source_file_count=len(paths),
        includes_biological_data=False, includes_checkpoints=False,
        scope='New review experiments and tests only; not a standalone research implementation.',
        requirements='Requires the existing BioCoLoop research checkout, original task adapters, '
            'registered candidate caches and locally authorized biological data. '
            'Historical dependencies are identified by the experiment provenance source hashes.',
        note='The stopped v1 canary, CPU scheduling benchmark and resource-only scheduler are '
            'included for auditability; their outputs are not formal v2 allocation results.')
    (OUT / 'experiment_sources.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'PASS: {len(paths)} Python source files; no data or checkpoints')


if __name__ == '__main__':
    main()
