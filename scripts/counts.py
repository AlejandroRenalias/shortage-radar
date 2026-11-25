"""Daily denominators, saved next to the ledger from the day they were first recorded.

The basic register describes only today, so the number of packages a company or a substitution group had on an earlier day cannot be
rebuilt later. `data/ledger/counts/YYYY-MM-DD.jsonl` keeps them, one file for each day, written whole and never changed. The first run of a
day writes that day; later runs on the same day add nothing, the same rule as the ledger. A day with no file was not recorded.
The rows of a day are made from the shortage file and the register that the ledger rows of that day were made from (their SHA-256), never from
newer files. The day is written to a temporary file and renamed, so a file with a day's name is always a whole day.

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
import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from build import ROOT, group_key, read_snapshot, register
from ledger import LEDGER, read_rows, sha256, snapshot_candidates
from source_age import register_date
from triage import is_available_alternative, on_market


def holder_name(text):
    return ' '.join((text or '').split())


def holder_pass(path, wanted):
    """One pass over the register: ({holder: Counter(on_market, on_market_vet)} over every package with `Kaupan` 1,
    {wanted VNR: (holder, is_vet)}). A VNR is found by its own number first, then by an old VNR, as in build.register."""
    market, owners, exact, listed, seen = Counter(), {}, set(), {}, set()
    for _, el in ET.iterparse(path, events=('end',)):
        if el.tag == 'Pakkaus':
            ref, vnr = el.get('Laakevalmiste-ref'), el.findtext('VNR-numero')
            # A VNR written twice in the register counts once, as in the ledger, which counts packages by VNR.
            if el.findtext('Kaupanolo/Kaupan') == '1' and not (vnr and vnr in seen):
                market[ref] += 1
                seen.add(vnr)
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
    # `alternatives` of a group is the value the ledger writes for its listed packages: `other_packages_count` of build.register, the same number, taken
    # from the lowest listed VNR of the group (the ledger check 2 requires all of them to be equal). There is no second calculation.
    group_alternatives = {}
    for v in sorted(vnrs):
        product = products.get(v)
        key = group_key(product) if product else None
        if key:
            group_alternatives.setdefault(key, product['other_packages_count'])
    for group in sorted(group_alternatives):
        packs = members.get(group, [])
        listed_vnrs = {p['vnr'] for p in packs if ({p['vnr']} | p['old']) & shortage_vnrs}
        # Holders: only records that are themselves available alternatives (a short duplicate of a VNR adds no holder).
        holders = {holder_name(p['company']) for p in packs if is_available_alternative(p, shortage_vnrs, day, True)}
        out.append({'date': day, 'type': 'group', 'group': group, 'on_market': len({p['vnr'] for p in packs if on_market(p, day)}), 'listed': len(listed_vnrs),
                    'alternatives': group_alternatives[group], 'distinct_alternative_holders': len(holders), 'register_date': ran})
    return out


class CountsInputError(ValueError):
    """The counts of a day cannot be made from the same inputs as the ledger rows of that day."""


DAY_FILE = re.compile(r'\d{4}-\d{2}-\d{2}\.jsonl')
TEMP_PREFIX = '.tmp-'


def counts_folder(folder=LEDGER):
    return folder / 'counts'


def check_file(path):
    """Raises ValueError when a counts file is not a complete day: it must be UTF-8, end with a newline, hold only JSON rows of the kind
    `company` or `group`, and every row must carry the date in the file's name. The archive job runs this before it stages a new file."""
    try:
        text = path.read_bytes().decode('utf-8')
    except UnicodeDecodeError as error:
        raise ValueError(f'not UTF-8: {error}') from None
    if not text or not text.endswith('\n'):
        raise ValueError('the last line is not complete')
    for number, line in enumerate(text.splitlines(), 1):
        try:
            row = json.loads(line)
            ok = row['type'] in ('company', 'group') and row['date'] == path.stem
        except (ValueError, KeyError, TypeError):
            ok = False
        if not ok:
            raise ValueError(f'line {number} is not a counts row of {path.stem}')


def inputs_of_the_ledger(day, folder, register_path, snapshot_folder):
    """The shortage rows of `day` as the ledger rows of that day saw them; CountsInputError when the register on disk or the shortage file are
    not the ones named by the SHA-256 in those rows. Counts and ledger rows of one day always come from the same two files."""
    rows = [r for r in read_rows(folder, canonical=False) if r['date'] == day]
    if not rows:
        raise CountsInputError(f'no ledger rows dated {day}: the counts of a day are made only from the inputs of its ledger rows')
    shortage_hashes, register_hashes = {r['shortages_sha256'] for r in rows}, {r['register_sha256'] for r in rows}
    dates = ', '.join(sorted({r['register_date'] for r in rows}))
    if not register_path.exists() or register_hashes != {sha256(register_path)}:
        raise CountsInputError(f'the register on disk is not the one the ledger rows of {day} were made with (register_date {dates}, SHA-256 {", ".join(sorted(register_hashes))})')
    for path in snapshot_candidates(day, snapshot_folder):
        if {sha256(path)} == shortage_hashes:
            return read_snapshot(path)
    raise CountsInputError(f'no shortage file has the SHA-256 {", ".join(sorted(shortage_hashes))} of the ledger rows of {day}')


def newest_ledger_day(folder):
    """The date of the newest ledger rows: the day the ledger step of this run just wrote. Counts do not read the clock, so a run that crosses midnight
    between the two steps still counts the day the ledger recorded."""
    days = {r['date'] for r in read_rows(folder, canonical=False)}
    if not days:
        raise CountsInputError('the ledger has no rows; the counts of a day are made only from the inputs of its ledger rows')
    return max(days)


def record(day=None, folder=LEDGER, register_path=ROOT / 'data/source/register.xml', snapshot_folder=None):
    """Write the count rows of `day` (default: the newest ledger day, see newest_ledger_day) to `<folder>/counts/<day>.jsonl`, once. The rows are made from the
    shortage file and the register that the ledger rows of that day were made from. The whole day is written to a temporary file in the same folder,
    flushed to disk and renamed, so a file with the day's name is always a complete day or does not exist. An existing day file is never touched.
    Returns the number of rows written; 0 when the day already has its file. Raises CountsInputError when the inputs are not on disk."""
    day = day or newest_ledger_day(folder)
    target_folder = counts_folder(folder)
    target_folder.mkdir(parents=True, exist_ok=True)
    for leftover in target_folder.glob(TEMP_PREFIX + '*'):
        leftover.unlink()  # what an interrupted run left behind; it was never a day file
    target = target_folder / f'{day}.jsonl'
    if target.exists():
        return 0
    rows = inputs_of_the_ledger(day, folder, register_path, snapshot_folder or ROOT / 'data/snapshots')
    new = rows_for(day, rows, register_path)
    temporary = target_folder / f'{TEMP_PREFIX}{day}'
    with temporary.open('w', encoding='utf-8', newline='\n') as f:
        f.write(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for r in new))
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, target)
    return len(new)


def read_days(folder=LEDGER):
    """{day: rows} of every day file `YYYY-MM-DD.jsonl` in the counts folder; temporary and other files are ignored."""
    out = {}
    for path in sorted(counts_folder(folder).glob('*.jsonl')):
        if DAY_FILE.fullmatch(path.name):
            out[path.stem] = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    return out


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', nargs='+', metavar='FILE', help='exit 1 when a counts day file is not complete')
    args = parser.parse_args(argv)
    if args.check:
        bad = 0
        for name in args.check:
            try:
                check_file(Path(name))
            except ValueError as error:
                print(f'::error::{name} is not a complete counts day: {error}')
                bad = 1
        return bad
    try:
        print(record())
    except CountsInputError as error:
        print(f'::error::Daily counts not written: {error}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
