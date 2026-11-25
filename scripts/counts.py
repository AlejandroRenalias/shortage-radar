"""Daily denominators, saved next to the ledger from the day they were first recorded.

The basic register describes only today, so the number of packages a company or a substitution group had on an earlier day cannot be
rebuilt later. `data/ledger/counts-YYYY-MM.jsonl` keeps them, one file for each month, rows only added, never rewritten. The first run of a
day writes that day; later runs on the same day add nothing, the same rule as the ledger. A day with no rows was not recorded.
The rows of a day are made from the shortage file and the register that the ledger rows of that day were made from (their SHA-256), never from
newer files, and the day is added to the file in one atomic step.

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
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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
    for group in sorted({group_key(p) for p in products.values()} - {None}):
        packs = list({p['vnr']: p for p in reversed(members.get(group, []))}.values())  # one package for each VNR, as the ledger counts them
        listed_packs = [p for p in packs if ({p['vnr']} | p['old']) & shortage_vnrs]
        if not listed_packs:
            continue
        alternatives = [p for p in packs if is_available_alternative(p, shortage_vnrs, day, True)]
        out.append({'date': day, 'type': 'group', 'group': group, 'on_market': sum(on_market(p, day) for p in packs), 'listed': len(listed_packs), 'alternatives': len(alternatives),
                    'distinct_alternative_holders': len({holder_name(p['company']) for p in alternatives}), 'register_date': ran})
    return out


class CountsInputError(ValueError):
    """The counts of a day cannot be made from the same inputs as the ledger rows of that day."""


def parse_lines(text):
    """The (line, row) pairs of a counts file. Raises ValueError when a line is not a complete counts row or the last line has no newline."""
    if text and not text.endswith('\n'):
        raise ValueError('the last line is not complete')
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        try:
            row = json.loads(line)
            row['date'], row['type']
        except (ValueError, KeyError, TypeError):
            raise ValueError(f'line {number} is not a counts row') from None
        rows.append((line, row))
    return rows


def check_file(path):
    """Raises ValueError when a counts file does not parse. The archive job runs this before it stages the file."""
    parse_lines(path.read_text(encoding='utf-8'))


def write_atomically(path, text):
    """Replace the file in one step, so an interrupted write leaves the old file and never half a line."""
    temporary = path.with_name(path.name + '.tmp')
    try:
        with temporary.open('w', encoding='utf-8', newline='\n') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def recover(path, day):
    """Repair a file whose last line was left incomplete by an interrupted run (an older writer, or damage): the incomplete line is removed, and so
    are the rows of `day` when that is the day being written, so the day is written again from the start. A bad line anywhere else is real damage
    and raises ValueError."""
    if not path.exists():
        return
    text = path.read_text(encoding='utf-8')
    try:
        parse_lines(text)
        return
    except ValueError:
        pass
    lines = text.split('\n')
    lines = lines[:-1]  # the text after the last newline is never trusted; it is empty when the file ended with one
    if lines and not lines[-1].strip():
        lines.pop()
    while lines:
        try:
            parse_lines(lines[-1] + '\n')
            break
        except ValueError:
            lines.pop()  # one incomplete line
            break
    rows = parse_lines(''.join(line + '\n' for line in lines))
    dropped_day = bool(rows) and rows[-1][1]['date'] == day
    if dropped_day:
        rows = [(line, row) for line, row in rows if row['date'] != day]
    print(f'::warning::{path.name} ended with an incomplete line; it was removed' + (f' together with the rows of {day}, which are written again' if dropped_day else ''))
    if rows:
        write_atomically(path, ''.join(line + '\n' for line, _ in rows))
    else:
        path.unlink()


def has_day(path, day):
    return path.exists() and any(row['date'] == day for _, row in parse_lines(path.read_text(encoding='utf-8')))


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


def record(day=None, folder=LEDGER, register_path=ROOT / 'data/source/register.xml', snapshot_folder=None):
    """Write the count rows of `day` (default: today in Helsinki, like the ledger) once, from the shortage file and the register that the ledger rows of
    that day were made from. Returns the number of rows written; 0 when the day is already in the file. Raises CountsInputError when those inputs
    are not on disk: a later run with a newer register does not write the day with it. The day is added in one atomic step."""
    day = day or datetime.now(ZoneInfo('Europe/Helsinki')).date().isoformat()
    path = folder / f'counts-{day[:7]}.jsonl'
    recover(path, day)
    if has_day(path, day):
        return 0
    rows = inputs_of_the_ledger(day, folder, register_path, snapshot_folder or ROOT / 'data/snapshots')
    new = rows_for(day, rows, register_path)
    folder.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding='utf-8') if path.exists() else ''
    write_atomically(path, old + ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for r in new))
    return len(new)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', nargs='+', metavar='FILE', help='exit 1 when a counts file does not parse')
    args = parser.parse_args(argv)
    if args.check:
        bad = 0
        for name in args.check:
            try:
                check_file(Path(name))
            except ValueError as error:
                print(f'::error::{name} does not parse: {error}')
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
