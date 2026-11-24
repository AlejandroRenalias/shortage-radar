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
from datetime import datetime
from zoneinfo import ZoneInfo

from build import ROOT, load_snapshots, register
from record_triage import register_date
from triage import level

LEDGER = ROOT / 'data/ledger'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def has_day(path, day):
    """Whether the month file already has rows for `day`."""
    if not path.exists():
        return False
    lines = path.read_text(encoding='utf-8').splitlines()
    return any(json.loads(line)['date'] == day for line in lines)


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
