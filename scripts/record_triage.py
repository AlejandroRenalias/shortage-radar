"""Record today's impact triage counts, so their history does not depend on a register that only describes today.

The basic register has no history: a later register may move a package to another group or off the market. These counts
are computed with the register of the day, the same way as the site, and kept in data/triage-counts.json, one entry per
snapshot date. A later run on the same date replaces that date's entry.
"""
import json

from build import ROOT, load_snapshots, register
from source_age import register_date
from triage import counts

PATH = ROOT / 'data/triage-counts.json'
NOTE = ('Impact triage counts of the latest snapshot, computed with the basic register of the day it was recorded. '
        'substitute: other packages in the substitution group are on the market and not short; critical: a group without such packages; '
        'nogroup: no substitution group; vet: veterinary medicines.')


def entry(day, rows, register_path):
    vnrs = {r['NordicArticleNumber'] for r in rows}
    products = register(register_path, vnrs, vnrs)
    current = [dict({'other_packages_count': 0}, **products.get(r['NordicArticleNumber'], {}), **r) for r in rows]
    return dict({'date': day, 'register_date': register_date(register_path), 'total': len(current)}, **counts(current))


def record(path=PATH, register_path=ROOT / 'data/source/register.xml'):
    snapshots, _ = load_snapshots()
    day, rows = snapshots[-1]
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'note': NOTE, 'counts': []}
    new = entry(day, rows, register_path)
    data['note'] = NOTE
    data['counts'] = sorted([c for c in data['counts'] if c['date'] != day] + [new], key=lambda c: c['date'])
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return new


if __name__ == '__main__':
    print(record())
