"""Record today's impact triage counts, so their history does not depend on a register that only describes today.

The basic register has no history: a later register may move a package to another group or off the market. These counts
are computed with the register of the day, the same way as the site, and kept in data/triage-counts.json, one entry per
snapshot date. A later run on the same date replaces that date's entry.
"""
import json

from build import ROOT, load_snapshots, register
from source_age import register_date
from triage import ALIASES, LEVELS, counts, with_aliases

PATH = ROOT / 'data/triage-counts.json'
NOTE = ('Impact triage counts of the latest snapshot, computed with the basic register of the day it was recorded. '
        'substitute: other packages in the substitution group are on the market and not short; no_alternative: a group without such packages; '
        'nogroup: no substitution group; vet: veterinary medicines. `critical` is the old name of no_alternative, kept with the same value for one release.')


def entry(day, rows, register_path):
    vnrs = {r['NordicArticleNumber'] for r in rows}
    products = register(register_path, vnrs, vnrs)
    current = [dict({'other_packages_count': 0}, **products.get(r['NordicArticleNumber'], {}), **r) for r in rows]
    return dict({'date': day, 'register_date': register_date(register_path), 'total': len(current)}, **with_aliases(counts(current)))


def migrate(c):
    """An entry recorded under the old level name gets the new key too, with the same value, in the order of triage.LEVELS."""
    c = dict(c, **{new: c[old] for old, new in ALIASES.items() if new not in c and old in c})
    order = ['date', 'register_date', 'total', *LEVELS, *ALIASES]
    return {k: c[k] for k in order if k in c} | {k: v for k, v in c.items() if k not in order}


def record(path=PATH, register_path=ROOT / 'data/source/register.xml'):
    snapshots, _ = load_snapshots()
    day, rows = snapshots[-1]
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'note': NOTE, 'counts': []}
    latest = entry(day, rows, register_path)
    data['note'] = NOTE
    kept = [migrate(c) for c in data['counts'] if c['date'] != day]
    data['counts'] = sorted(kept + [latest], key=lambda c: c['date'])
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return latest


if __name__ == '__main__':
    print(record())
