"""Daily validation of the ledger, run by the archive job right after the ledger step and before anything is published.

Eight checks read the day's ledger rows (and the month file, the register and the snapshot they came from). A check is FAIL, WARN or
PASS; SKIP means it could not be judged (see check 1 and 5). A failed check never deletes or changes data: this script only reads,
prints one line for each check (`::error::` for FAIL, `::warning::` for WARN) and exits 1 when a check failed. The archive job then opens or
updates the `data-validation` entry of the data-pipeline issue (scripts/pipeline_alert.py) and closes it when the checks pass again.
A WARN is written to the run log and does not open the issue.

1. Every ledger VNR joins to the register (VNR or old VNR).                                  FAIL
2. `alternatives` is the same for all packages of a group; null exactly when the group is empty. FAIL
3. No duplicate (date, vnr) in the month file.                                               FAIL
4. The row count is within 10% of the previous recorded day.                                 WARN
5. `alternatives` never exceeds the number of other packages of the group in the register.   FAIL
6. `register_date` of the day's rows equals the ledger `date`, or is at most STALE_DAYS old. WARN when older.
7. The ledger VNR set equals the snapshot's VNR set and `shortages_sha256` is the snapshot's hash. FAIL
8. `impact` is one of the allowed values (`critical` only in rows of days up to LAST_CRITICAL_DAY). FAIL

The register changes about once a day. A later run of the same day may have downloaded a newer register than the one the ledger rows
were made with (their `register_sha256`); checks 1 and 5 compare with the register, so they are SKIP then (`--force-register` runs them anyway).
"""
import argparse
import json
import os
import sys
from collections import namedtuple
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build import ROOT, group_key, read_snapshot, register
from ledger import LEDGER, read_rows, sha256
from source_age import STALE_DAYS, iso_day
from triage import LEVELS

ROW_CHANGE_LIMIT = 0.10
# The last day whose ledger rows carry the old level name `critical` (the rename to `no_alternative` first shows on 25 Nov 2026).
LAST_CRITICAL_DAY = '2026-11-24'
ALLOWED_IMPACT = set(LEVELS)
EXAMPLES = 5

Result = namedtuple('Result', 'number name status message')


def examples(items):
    items = sorted(items, key=str)
    return ', '.join(map(str, items[:EXAMPLES])) + (f' and {len(items) - EXAMPLES} more' if len(items) > EXAMPLES else '')


def verdict(number, name, bad, fail_status, ok='ok', problem=''):
    """PASS when `bad` is empty; else `fail_status` ('FAIL' or 'WARN') with the first examples."""
    if not bad:
        return Result(number, name, 'PASS', ok)
    return Result(number, name, fail_status, f'{problem} {len(bad)}: {examples(bad)}'.strip())


def check_join(rows, joined):
    """1. Every ledger VNR is a VNR or old VNR of a register package. `joined` is the set of the VNRs that did."""
    return verdict(1, 'ledger VNRs join to the register', {r['vnr'] for r in rows} - set(joined), 'FAIL', f'{len(rows)} rows join', 'not in the register:')


def check_alternatives_per_group(rows):
    """2. All packages of a group have the same `alternatives`, and `alternatives` is null exactly when `group` is empty."""
    by_group, bad = {}, []
    for r in rows:
        if bool(r['group']) != (r['alternatives'] is not None):
            bad.append(f"{r['vnr']} (group {r['group']!r}, alternatives {r['alternatives']!r})")
        if r['group']:
            by_group.setdefault(r['group'], set()).add(r['alternatives'])
    bad += [f'group {g} has {sorted(v, key=str)}' for g, v in by_group.items() if len(v) > 1]
    return verdict(2, '`alternatives` equal inside a group, null without a group', bad, 'FAIL', f'{len(by_group)} groups consistent', 'inconsistent:')


def check_duplicates(month_rows):
    """3. No (date, vnr) twice in the month file."""
    seen, dup = set(), set()
    for r in month_rows:
        key = (r['date'], r['vnr'])
        (dup if key in seen else seen).add(key)
    return verdict(3, 'no duplicate (date, vnr)', [f'{d} {v}' for d, v in dup], 'FAIL', f'{len(month_rows)} rows, no duplicate', 'duplicates:')


def check_row_count(rows, previous_count, previous_day=None):
    """4. The row count is within ROW_CHANGE_LIMIT of the previous recorded day (WARN otherwise; nothing to compare with is a PASS)."""
    if not previous_count:
        return Result(4, 'row count near the previous day', 'PASS', f'{len(rows)} rows, no earlier recorded day to compare with')
    change = (len(rows) - previous_count) / previous_count
    text = f'{len(rows)} rows against {previous_count} on {previous_day} ({change:+.1%})'
    return Result(4, 'row count near the previous day', 'PASS' if abs(change) <= ROW_CHANGE_LIMIT else 'WARN', text)


def check_other_packages(rows, others):
    """5. `alternatives` is at most the number of other packages of the group in the register. `others` is {vnr: that number}."""
    bad = [f"{r['vnr']} (alternatives {r['alternatives']}, other packages {others.get(r['vnr'], 0)})" for r in rows if r['group'] and (r['alternatives'] or 0) > others.get(r['vnr'], 0)]
    return verdict(5, '`alternatives` at most the other packages of the group', bad, 'FAIL', 'ok', 'too many:')


def check_register_date(rows, day, limit=STALE_DAYS):
    """6. The rows' `register_date` equals the ledger `date`, or is at most `limit` days older (WARN when older or unreadable)."""
    dates = {r['register_date'] for r in rows}
    ledger_day = date.fromisoformat(day)
    old = []
    for d in sorted(dates):
        parsed = iso_day(d)
        if not parsed or (ledger_day - parsed).days > limit:
            old.append(d or 'none')
    if old:
        return Result(6, 'register date current', 'WARN', f'register_date {examples(old)} is older than {limit} days or unreadable for the ledger date {day}')
    lag = max((ledger_day - iso_day(d)).days for d in dates) if dates else 0
    return Result(6, 'register date current', 'PASS', f'register_date {examples(dates)}' + (f' ({lag} day older than the ledger date, within the limit of {limit})' if lag else ''))


def check_snapshot(rows, snapshot_vnrs, snapshot_sha, label='the snapshot'):
    """7. The ledger VNR set equals the snapshot's VNR set, and `shortages_sha256` is the snapshot file's hash."""
    ledger_vnrs, shas = {r['vnr'] for r in rows}, {r['shortages_sha256'] for r in rows}
    bad = []
    if ledger_vnrs != set(snapshot_vnrs):
        bad.append(f'VNR sets differ: only in the ledger {examples(ledger_vnrs - set(snapshot_vnrs)) or "none"}; only in {label} {examples(set(snapshot_vnrs) - ledger_vnrs) or "none"}')
    if shas != {snapshot_sha}:
        bad.append(f'shortages_sha256 {examples(shas)} is not {snapshot_sha}')
    return verdict(7, 'ledger matches the snapshot', bad, 'FAIL', f'same {len(ledger_vnrs)} VNRs and hash as {label}', 'mismatch:')


def check_impact_values(month_rows):
    """8. `impact` is one of the levels; the old `critical` only in rows dated up to LAST_CRITICAL_DAY."""
    bad = [f"{r['date']} {r['vnr']} {r['impact']!r}" for r in month_rows if r['impact'] not in ALLOWED_IMPACT and not (r['impact'] == 'critical' and r['date'] <= LAST_CRITICAL_DAY)]
    return verdict(8, 'impact values allowed', bad, 'FAIL', 'ok', 'not allowed:')


def helsinki_today():
    return datetime.now(ZoneInfo('Europe/Helsinki')).date().isoformat()


def snapshot_file(day, folder):
    """The snapshot the ledger used on `day`: the latest saved capture dated on or before it (own files before imported ones, as build.load_snapshots)."""
    own = {p.stem: p for p in folder.glob('????-??-??.txt')}
    earlier = {p.stem: p for p in (folder / 'imported').glob('????-??-??.txt') if p.stem not in own}
    paths = {**earlier, **own}
    days = [d for d in paths if d <= day]
    return paths[max(days)] if days else None


def snapshot_for(rows, day, folder):
    """(VNR set, SHA-256, label) of the file the rows should match: the day's snapshot, or the file a same-day refetch replaced when the
    ledger was written before it (data/snapshots/superseded/<day>T<time>Z-<hash>.txt; the hash in the rows decides)."""
    path = snapshot_file(day, folder)
    if path is None:
        return None
    digest = sha256(path)
    shas = {r['shortages_sha256'] for r in rows}
    if digest not in shas:
        for old in sorted((folder / 'superseded').glob(f'{day}T*.txt')):
            if sha256(old) in shas:
                return {r['NordicArticleNumber'] for r in read_snapshot(old)}, sha256(old), f'the superseded file {old.name}'
    return {r['NordicArticleNumber'] for r in read_snapshot(path)}, digest, f'the snapshot {path.name}'


def register_facts(rows, register_path, day):
    """(set of the ledger VNRs that join to the register, {vnr: number of other packages in its group}), read from the register."""
    vnrs = {r['vnr'] for r in rows}
    members = {}
    products = register(register_path, vnrs, vnrs, members=members, day=day)
    others = {}
    for v, product in products.items():
        key = group_key(product)
        others[v] = len([p for p in members.get(key, []) if p['vnr'] != product['current_vnr']]) if key else 0
    return set(products), others


def run(day, ledger_folder=LEDGER, register_path=ROOT / 'data/source/register.xml', snapshot_folder=ROOT / 'data/snapshots', force_register=False):
    """The results of the eight checks for the ledger rows of `day`. Reads only; changes nothing."""
    month_rows = read_rows(ledger_folder, canonical=False)
    rows = [r for r in month_rows if r['date'] == day]
    if not rows:
        return [Result(0, 'ledger has rows for the day', 'FAIL', f'no ledger rows dated {day}: the ledger step did not write them')]
    month = [r for r in month_rows if r['date'][:7] == day[:7]]
    earlier = sorted({r['date'] for r in month_rows if r['date'] < day})
    previous = earlier[-1] if earlier else None
    results = [check_alternatives_per_group(rows), check_duplicates(month)]
    results.append(check_row_count(rows, sum(1 for r in month_rows if r['date'] == previous), previous))
    results.append(check_register_date(rows, day))
    snap = snapshot_for(rows, day, snapshot_folder)
    results.append(check_snapshot(rows, *snap) if snap else Result(7, 'ledger matches the snapshot', 'FAIL', f'no snapshot dated on or before {day}'))
    results.append(check_impact_values(month))
    hashes = {r['register_sha256'] for r in rows}
    if not register_path.exists():
        for n, name in ((1, 'ledger VNRs join to the register'), (5, '`alternatives` at most the other packages of the group')):
            results.append(Result(n, name, 'SKIP', 'no register file'))
    elif hashes != {sha256(register_path)} and not force_register:
        for n, name in ((1, 'ledger VNRs join to the register'), (5, '`alternatives` at most the other packages of the group')):
            results.append(Result(n, name, 'SKIP', 'the register file is not the one the ledger rows were made with (a later run of the day downloaded a newer one)'))
    else:
        joined, others = register_facts(rows, register_path, day)
        results += [check_join(rows, joined), check_other_packages(rows, others)]
    return sorted(results)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--day', default=None, help='ledger date to check (default: today in Helsinki)')
    parser.add_argument('--register', default=str(ROOT / 'data/source/register.xml'))
    parser.add_argument('--force-register', action='store_true', help='run checks 1 and 5 even when the register is not the one the rows were made with')
    args = parser.parse_args(argv)
    day = args.day or helsinki_today()
    try:
        results = run(day, register_path=Path(args.register), force_register=args.force_register)
    except Exception as error:  # a validation that cannot run is reported, not hidden
        print(f'::error::Daily validation could not run: {error!r}')
        status = 'error'
        results = []
    else:
        for r in results:
            line = f'check {r.number} {r.status}: {r.name}: {r.message}'
            print({'FAIL': '::error::', 'WARN': '::warning::'}.get(r.status, '') + line)
        failed = [r for r in results if r.status == 'FAIL']
        status = 'fail' if failed else 'pass'
        print(f'Daily validation for {day}: {len(failed)} failed, {sum(r.status == "WARN" for r in results)} warned, {sum(r.status == "SKIP" for r in results)} skipped, {sum(r.status == "PASS" for r in results)} passed. Data was not changed.')
    # The workflow opens the data-validation alert on fail or error and closes it on pass.
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
            f.write(f'status={status}\n')
    print(f'status={status}')
    return 0 if status == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
