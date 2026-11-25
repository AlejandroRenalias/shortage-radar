"""Daily denominators, saved next to the ledger from the day they were first recorded.

The basic register describes only today, so the number of packages a company or a substitution group had on an earlier day cannot be
rebuilt later. `data/ledger/counts-YYYY-MM.jsonl` keeps them, one file for each month, rows only added, never rewritten. The first run of a
day writes that day; later runs on the same day add nothing, the same rule as the ledger. A day with no rows was not recorded.

A day has two kinds of rows, `type` "company" and `type` "group", in this order: companies by name, then groups by code.

- company: one row for each register holder (`Myyntilupa/Haltija`) with at least one package on the shortage list:
  `listed` (packages on the shortage list, one for each VNR), `on_market` (register packages with `Kaupan` 1), each also split in
  `_human` and `_vet` (veterinary: ATC starting with Q, as in triage.level), and `register_date`.
- group: one row for each substitution group with at least one listed package: `on_market` (packages of the group on the market by
  triage.on_market on that day), `listed`, `alternatives` (packages of the group that triage.is_available_alternative accepts, the
  value the ledger writes for the group), `distinct_alternative_holders` (distinct register holders among those alternatives)
  and `register_date`.

No second definition is made here: the market and alternative rules are the ones in scripts/triage.py.
"""
import json
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

from build import ROOT, group_key, load_snapshots, register
from ledger import LEDGER, has_day
from source_age import register_date
from triage import is_available_alternative, on_market


def holder_name(text):
    return ' '.join((text or '').split())


def holder_pass(path, wanted):
    """One pass over the register: ({holder: Counter(on_market, on_market_vet)} over every package with `Kaupan` 1,
    {wanted VNR: (holder, is_vet)}). A VNR is found by its own number first, then by an old VNR, as in build.register."""
    market, owners, exact, listed = Counter(), {}, set(), {}
    for _, el in ET.iterparse(path, events=('end',)):
        if el.tag == 'Pakkaus':
            ref, vnr = el.get('Laakevalmiste-ref'), el.findtext('VNR-numero')
            if el.findtext('Kaupanolo/Kaupan') == '1':
                market[ref] += 1
            if vnr in wanted:
                listed[vnr] = ref
                exact.add(vnr)
            for old in (x.text for x in el.findall('VanhaVNR')):
                if old in wanted and old not in exact and (old not in listed or vnr):
                    listed[old] = ref
            el.clear()
        elif el.tag == 'Laakevalmiste':
            atc = el.find('ATC-koodi')
            owners[el.get('id')] = (holder_name(el.findtext('Myyntilupa/Haltija', '')), (atc.get('id', '') if atc is not None else '').startswith('Q'))
            el.clear()
    on_market_by_holder = {}
    for ref, n in market.items():
        holder, vet = owners.get(ref, ('', False))
        c = on_market_by_holder.setdefault(holder, Counter())
        c['on_market'] += n
        c['on_market_vet'] += n if vet else 0
    return on_market_by_holder, {v: owners.get(ref, ('', False)) for v, ref in listed.items()}


def rows_for(day, rows, register_path):
    """The count rows of `day` for the shortage rows `rows`, from the register file `register_path`."""
    vnrs = {r['NordicArticleNumber'] for r in rows}
    members = {}
    products = register(register_path, vnrs, vnrs, members=members, day=day)
    ran = register_date(register_path)
    on_market_by_holder, owner = holder_pass(register_path, vnrs)
    # Listed packages: one for each VNR of the file; the company is the register holder of the package.
    listed = {}
    for v in sorted(vnrs):
        holder, vet = owner.get(v, ('', False))
        if not holder:
            continue  # a VNR the register does not know (ledger check 1 reports it) has no holder to count
        c = listed.setdefault(holder, Counter())
        c['listed'] += 1
        c['listed_vet'] += vet
    out = []
    for holder in sorted(listed):
        c, m = listed[holder], on_market_by_holder.get(holder, Counter())
        out.append({'date': day, 'type': 'company', 'company': holder, 'listed': c['listed'], 'listed_human': c['listed'] - c['listed_vet'], 'listed_vet': c['listed_vet'],
                    'on_market': m['on_market'], 'on_market_human': m['on_market'] - m['on_market_vet'], 'on_market_vet': m['on_market_vet'], 'register_date': ran})
    shortage_vnrs = set(vnrs)
    for group in sorted({group_key(p) for p in products.values()} - {None}):
        packs = members.get(group, [])
        listed_packs = [p for p in packs if ({p['vnr']} | p['old']) & shortage_vnrs]
        if not listed_packs:
            continue
        alternatives = [p for p in packs if is_available_alternative(p, shortage_vnrs, day, True)]
        out.append({'date': day, 'type': 'group', 'group': group, 'on_market': sum(on_market(p, day) for p in packs), 'listed': len(listed_packs), 'alternatives': len(alternatives),
                    'distinct_alternative_holders': len({holder_name(p['company']) for p in alternatives}), 'register_date': ran})
    return out


def record(day=None, folder=LEDGER, register_path=ROOT / 'data/source/register.xml'):
    """Append the count rows of `day` (default: today in Helsinki, like the ledger) from the latest snapshot and the register file.
    Returns the number of rows written; 0 when the day is already in the file."""
    day = day or datetime.now(ZoneInfo('Europe/Helsinki')).date().isoformat()
    path = folder / f'counts-{day[:7]}.jsonl'
    if has_day(path, day):
        return 0
    snapshots, _ = load_snapshots()
    new = rows_for(day, snapshots[-1][1], register_path)
    folder.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8', newline='\n') as f:
        f.write(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for r in new))
    return len(new)


if __name__ == '__main__':
    print(record())
