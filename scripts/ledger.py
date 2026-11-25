"""Daily ledger: what the archive saw each day, one row per package in the shortage file, appended and never rewritten.

`data/ledger/YYYY-MM.jsonl` holds one JSON object per line. Each row has the check `date`, the package `vnr`, its substitution
`group` (empty when none), its `impact` level, the number of `alternatives` (other packages in the group on the market and not
short; null when there is no group), the `register_date` of the basic register used, and the SHA-256 of the two source files
(`shortages_sha256`, `register_sha256`) so a row can be tied to the files it came from.

A VNR with several notices in the file gets one row: the notice with the latest notification date (then the latest start date, then the company).
The job can run several times a day. The first run of a day writes its rows; later runs on that day add nothing, so a day is
never listed twice. A day is never changed afterwards, so rows written before `critical` was renamed `no_alternative`
keep the old name in `impact`; the two names are one level. The ledger describes only what the files said on the day; a gap in the
dates means the job did not record those days.
"""
import hashlib
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from build import ROOT, load_snapshots, register
from record_triage import register_date
from triage import canonical_impact, level

LEDGER = ROOT / 'data/ledger'
MONTH_FILE = re.compile(r'\d{4}-\d{2}\.jsonl')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def has_day(path, day):
    """Whether the month file already has rows for `day`."""
    if not path.exists():
        return False
    lines = path.read_text(encoding='utf-8').splitlines()
    return any(json.loads(line)['date'] == day for line in lines)


def read_rows(folder=LEDGER, canonical=True):
    """Every ledger row of the month files `YYYY-MM.jsonl`, oldest first (other files in the folder, such as the counts files, are not read).
    With `canonical` (the default) `impact` is passed through triage.canonical_impact, so rows written before the rename of `critical`
    read as `no_alternative`; every history query uses this default. Validation reads the written value (`canonical=False`)."""
    out = []
    for path in sorted(folder.glob('????-??.jsonl')):
        if not MONTH_FILE.fullmatch(path.name):
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                row = json.loads(line)
                out.append(dict(row, impact=canonical_impact(row['impact'])) if canonical else row)
    return out


def snapshot_candidates(day, folder):
    """The files a ledger row of `day` can come from, most likely first: the latest capture dated on or before `day` (own files before imported ones,
    as build.load_snapshots), the files a same-day refetch replaced (data/snapshots/superseded/<day>T<time>Z-<hash>.txt), and the latest capture dated
    before `day`. The last one is what the first run of the day used when the file had not changed since an earlier day and a later run of the day
    saved the day's own capture (archive.py moves nothing to superseded then)."""
    own = {p.stem: p for p in folder.glob('????-??-??.txt')}
    earlier = {p.stem: p for p in (folder / 'imported').glob('????-??-??.txt') if p.stem not in own}
    paths = {**earlier, **own}
    found = []
    on_or_before = [d for d in paths if d <= day]
    if on_or_before:
        found.append(paths[max(on_or_before)])
    found += sorted((folder / 'superseded').glob(f'{day}T*.txt'))
    before = [d for d in paths if d < day]
    if before and paths[max(before)] not in found:
        found.append(paths[max(before)])
    return found


def rows_for(day, rows, register_path, shortage_path):
    vnrs = {r['NordicArticleNumber'] for r in rows}
    products = register(register_path, vnrs, vnrs)
    hashes = {'shortages_sha256': sha256(shortage_path), 'register_sha256': sha256(register_path)}
    # One row for each VNR: when a VNR has several notices, the one with the latest notification date wins, then the latest
    # start date, then the company name, so the same file always gives the same row.
    chosen = {}
    for r in rows:
        key = (r['DateOfTheNotification'], r['UnavailableFrom'], r['Company'])
        if r['NordicArticleNumber'] not in chosen or key > chosen[r['NordicArticleNumber']][0]:
            chosen[r['NordicArticleNumber']] = (key, r)
    out = []
    for _, r in chosen.values():
        product = dict({'other_packages_count': 0}, **products.get(r['NordicArticleNumber'], {}), **r)
        group = product.get('substitution_group') or ''
        out.append(dict({'date': day, 'vnr': r['NordicArticleNumber'], 'group': group, 'impact': level(product),
                         'alternatives': product['other_packages_count'] if group else None, 'register_date': register_date(register_path)}, **hashes))
    return sorted(out, key=lambda x: x['vnr'])


def record(day=None, folder=LEDGER, register_path=ROOT / 'data/source/register.xml'):
    """Append the rows of `day` (default: today in Helsinki, as the archive dates its snapshots) from the latest snapshot.
    Returns the number of rows written; 0 when the day is already in the ledger."""
    day = day or datetime.now(ZoneInfo('Europe/Helsinki')).date().isoformat()
    path = folder / f'{day[:7]}.jsonl'
    if has_day(path, day):
        return 0
    snapshots, imported = load_snapshots()
    latest, rows = snapshots[-1]
    shortage_path = ROOT / 'data/snapshots' / ('imported' if latest in imported else '') / f'{latest}.txt'
    new = rows_for(day, rows, register_path, shortage_path)
    folder.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8', newline='\n') as f:
        f.write(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for r in new))
    return len(new)


if __name__ == '__main__':
    print(record())
