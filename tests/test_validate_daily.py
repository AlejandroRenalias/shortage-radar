import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build
import counts
import ledger
import triage
import validate_daily as v
from test_ledger import REGISTER, SNAPSHOT

DAY = '2026-11-23'


def row(vnr='012345', group='0042', alternatives=1, impact='substitute', register_date=DAY, date=DAY, sha='s'):
    return {'date': date, 'vnr': vnr, 'group': group, 'impact': impact, 'alternatives': alternatives, 'register_date': register_date, 'shortages_sha256': sha, 'register_sha256': 'r'}


def status(result):
    return result.status


# 1 join to the register
def test_check_1_join():
    assert status(v.check_join([row('1'), row('2')], {'1', '2', '3'})) == 'PASS'
    failing = v.check_join([row('1'), row('2')], {'1'})
    assert status(failing) == 'FAIL' and '2' in failing.message


# 2 alternatives equal inside a group; null exactly when the group is empty
def test_check_2_alternatives_per_group():
    assert status(v.check_alternatives_per_group([row('1', alternatives=2), row('2', alternatives=2), row('3', group='', alternatives=None, impact='nogroup')])) == 'PASS'
    assert status(v.check_alternatives_per_group([row('1', alternatives=2), row('2', alternatives=3)])) == 'FAIL'
    assert status(v.check_alternatives_per_group([row('1', group='', alternatives=0)])) == 'FAIL'
    assert status(v.check_alternatives_per_group([row('1', group='0042', alternatives=None)])) == 'FAIL'


# 3 duplicates
def test_check_3_duplicates():
    assert status(v.check_duplicates([row('1'), row('2'), row('1', date='2026-11-24')])) == 'PASS'
    assert status(v.check_duplicates([row('1'), row('2'), row('1')])) == 'FAIL'


# 4 row count within 10 % of the previous recorded day (WARN)
def test_check_4_row_count():
    assert status(v.check_row_count([row()] * 109, 100, '2026-11-22')) == 'PASS'
    assert status(v.check_row_count([row()] * 91, 100, '2026-11-22')) == 'PASS'
    assert status(v.check_row_count([row()] * 89, 100, '2026-11-22')) == 'WARN'
    assert status(v.check_row_count([row()] * 111, 100, '2026-11-22')) == 'WARN'
    assert status(v.check_row_count([row()] * 5, 0)) == 'PASS'  # no earlier recorded day: nothing to compare


# 5 alternatives never exceed the other packages of the group in the register
def test_check_5_other_packages():
    assert status(v.check_other_packages([row('1', alternatives=2)], {'1': 2})) == 'PASS'
    assert status(v.check_other_packages([row('1', alternatives=3)], {'1': 2})) == 'FAIL'
    assert status(v.check_other_packages([row('1', group='', alternatives=None)], {})) == 'PASS'


# 6 register date (WARN)
def test_check_6_register_date():
    assert status(v.check_register_date([row(register_date=DAY)], DAY)) == 'PASS'
    one_day = v.check_register_date([row(register_date='2026-11-22')], DAY)
    assert status(one_day) == 'PASS' and '1 day older' in one_day.message
    assert status(v.check_register_date([row(register_date='2026-11-21')], DAY)) == 'PASS'  # exactly STALE_DAYS old
    assert status(v.check_register_date([row(register_date='2026-11-20')], DAY)) == 'WARN'
    assert status(v.check_register_date([row(register_date='')], DAY)) == 'WARN'


# 7 snapshot VNR set and hash
def test_check_7_snapshot():
    rows = [row('1', sha='h'), row('2', sha='h')]
    assert status(v.check_snapshot(rows, {'1', '2'}, 'h')) == 'PASS'
    assert status(v.check_snapshot(rows, {'1', '2', '3'}, 'h')) == 'FAIL'
    assert status(v.check_snapshot(rows, {'1', '2'}, 'other')) == 'FAIL'


# 8 impact values
def test_check_8_impact():
    assert status(v.check_impact_values([row(impact=i) for i in ('substitute', 'no_alternative', 'nogroup', 'vet')])) == 'PASS'
    assert status(v.check_impact_values([row(impact='critical', date='2026-11-24')])) == 'PASS'  # an old row
    assert status(v.check_impact_values([row(impact='critical', date='2026-11-25')])) == 'FAIL'  # a row after the rename
    assert status(v.check_impact_values([row(impact='unknown')])) == 'FAIL'


def test_old_critical_is_read_as_no_alternative_in_one_shared_helper(tmp_path):
    assert triage.canonical_impact('critical') == 'no_alternative'
    assert [triage.canonical_impact(x) for x in ('no_alternative', 'substitute', 'nogroup', 'vet')] == ['no_alternative', 'substitute', 'nogroup', 'vet']
    # The counts of the site use the same helper.
    assert triage.counts([{'impact': 'critical'}, {'impact': 'no_alternative'}])['no_alternative'] == 2
    # Every history query reads the ledger through read_rows, which maps the old name; the written rows are not changed.
    (tmp_path / '2026-11.jsonl').write_text(json.dumps(row(impact='critical', date='2026-11-24')) + '\n' + json.dumps(row(impact='no_alternative', date='2026-11-25')) + '\n', encoding='utf-8')
    (tmp_path / 'counts-2026-11.jsonl').write_text('{"not": "a ledger row"}\n', encoding='utf-8')
    assert [r['impact'] for r in ledger.read_rows(tmp_path)] == ['no_alternative', 'no_alternative']
    assert [r['impact'] for r in ledger.read_rows(tmp_path, canonical=False)] == ['critical', 'no_alternative']
    assert 'critical' in (tmp_path / '2026-11.jsonl').read_text(encoding='utf-8')


# the whole run on a real ledger written by ledger.record
def setup(tmp_path, monkeypatch):
    (tmp_path / 'data/snapshots').mkdir(parents=True)
    (tmp_path / 'data/snapshots/2026-11-22.txt').write_text(SNAPSHOT, encoding='utf-8')
    register = tmp_path / 'register.xml'
    register.write_text(REGISTER, encoding='utf-8')
    monkeypatch.setattr(build, 'ROOT', tmp_path)
    monkeypatch.setattr(ledger, 'ROOT', tmp_path)
    monkeypatch.setattr(counts, 'ROOT', tmp_path)
    ledger.record(DAY, tmp_path / 'ledger', register)
    counts.record(DAY, tmp_path / 'ledger', register)
    return register, tmp_path / 'ledger', tmp_path / 'data/snapshots'


def results(register, folder, snaps, **kw):
    return {r.number: r for r in v.run(DAY, folder, register, snaps, **kw)}


def test_run_passes_on_a_ledger_written_by_the_ledger_script(tmp_path, monkeypatch):
    register, folder, snaps = setup(tmp_path, monkeypatch)
    found = results(register, folder, snaps)
    # The fixture register has no holder, so the counts list no company; check 12 warns about it (and only warns). Check 10 runs only when `today` is given.
    assert {n: r.status for n, r in found.items()} == {**dict.fromkeys([*range(1, 10), 11], 'PASS'), 12: 'WARN'}
    assert {n: r.status for n, r in results(register, folder, snaps, today=DAY).items()} == {**dict.fromkeys(range(1, 12), 'PASS'), 12: 'WARN'}


def test_run_reports_without_changing_any_file(tmp_path, monkeypatch):
    register, folder, snaps = setup(tmp_path, monkeypatch)
    month = folder / f'{DAY[:7]}.jsonl'
    lines = month.read_text(encoding='utf-8').splitlines()
    month.write_text('\n'.join(lines + [lines[0]]) + '\n', encoding='utf-8')  # a duplicate row
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert results(register, folder, snaps)[3].status == 'FAIL'
    assert {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()} == before


def test_run_fails_when_the_snapshot_differs_and_accepts_a_same_day_refetch(tmp_path, monkeypatch):
    register, folder, snaps = setup(tmp_path, monkeypatch)
    old = (snaps / '2026-11-22.txt').read_bytes()
    (snaps / '2026-11-22.txt').write_text(SNAPSHOT + '012346;K;2026-11-01;2026-12-01;2026-10-01;2026-11-01;Company\n', encoding='utf-8')
    assert results(register, folder, snaps)[7].status == 'FAIL'
    # The refetch keeps the replaced file as a superseded file dated like the ledger day; the rows match it.
    (snaps / 'superseded').mkdir()
    (snaps / 'superseded' / f'{DAY}T120000Z-{hashlib.sha256(old).hexdigest()[:12]}.txt').write_bytes(old)
    assert results(register, folder, snaps)[7].status == 'PASS'


def test_run_skips_the_register_checks_when_the_register_changed_and_runs_them_when_forced(tmp_path, monkeypatch):
    register, folder, snaps = setup(tmp_path, monkeypatch)
    register.write_text(REGISTER.replace('<Ajopvm>2026-11-23', '<Ajopvm>2026-11-24'), encoding='utf-8')
    found = results(register, folder, snaps)
    assert found[1].status == found[5].status == 'SKIP'
    forced = results(register, folder, snaps, force_register=True)
    assert forced[1].status == forced[5].status == 'PASS'
    # A VNR that left the register no longer joins, and the forced check says so.
    register.write_text(REGISTER.replace('012347', '999999'), encoding='utf-8')
    assert results(register, folder, snaps, force_register=True)[1].status == 'FAIL'


def test_run_fails_when_the_day_has_no_rows(tmp_path, monkeypatch):
    register, folder, snaps = setup(tmp_path, monkeypatch)
    found = v.run('2026-11-30', folder, register, snaps)
    assert [(r.number, r.status) for r in found] == [(0, 'FAIL')]


def test_main_prints_the_status_and_exits_1_only_for_a_failure(tmp_path, monkeypatch, capsys):
    out = tmp_path / 'output.txt'
    monkeypatch.setenv('GITHUB_OUTPUT', str(out))
    monkeypatch.setattr(v, 'run', lambda day, **kw: [v.Result(1, 'x', 'PASS', 'ok')])
    assert v.main(['--day', DAY]) == 0 and out.read_text(encoding='utf-8').splitlines()[-1] == 'status=pass'
    monkeypatch.setattr(v, 'run', lambda day, **kw: [v.Result(3, 'x', 'FAIL', 'duplicates: 1'), v.Result(4, 'y', 'WARN', 'rows')])
    assert v.main(['--day', DAY]) == 1
    text = capsys.readouterr().out
    assert '::error::check 3 FAIL' in text and '::warning::check 4 WARN' in text and 'Data was not changed' in text
    assert out.read_text(encoding='utf-8').splitlines()[-1] == 'status=fail'

    def broken(day, **kw):
        raise ValueError('broken')
    monkeypatch.setattr(v, 'run', broken)
    assert v.main(['--day', DAY]) == 1 and out.read_text(encoding='utf-8').splitlines()[-1] == 'status=error'
    # A WARN alone does not fail.
    monkeypatch.setattr(v, 'run', lambda day, **kw: [v.Result(4, 'y', 'WARN', 'rows')])
    assert v.main(['--day', DAY]) == 0


def test_the_workflow_runs_the_validation_after_the_ledger_and_before_the_commit():
    text = (Path(__file__).resolve().parents[1] / '.github/workflows/archive.yml').read_text(encoding='utf-8')
    assert text.index('python scripts/ledger.py') < text.index('python scripts/counts.py\n') < text.index('python scripts/validate_daily.py') < text.index('name: Commit changes')
    assert 'python scripts/counts.py' in text and 'PIPELINE=data-validation RESULT=failure' in text and 'PIPELINE=data-validation RESULT=success' in text
    from pipeline_alert import MEANING
    assert 'data-validation' in MEANING


def test_check_7_accepts_the_capture_of_an_earlier_day_that_the_first_run_of_the_day_used(tmp_path, monkeypatch):
    # Saturday's capture; the first Sunday run downloads the same bytes, so no Sunday file exists and the ledger uses Saturday's.
    (tmp_path / 'data/snapshots').mkdir(parents=True)
    (tmp_path / 'data/snapshots/2026-11-21.txt').write_text(SNAPSHOT, encoding='utf-8')
    register = tmp_path / 'register.xml'
    register.write_text(REGISTER, encoding='utf-8')
    monkeypatch.setattr(build, 'ROOT', tmp_path)
    monkeypatch.setattr(ledger, 'ROOT', tmp_path)
    ledger.record(DAY, tmp_path / 'ledger', register)
    folder, snaps = tmp_path / 'ledger', tmp_path / 'data/snapshots'
    assert results(register, folder, snaps)[7].status == 'PASS'
    # A later Sunday run finds changed bytes and saves Sunday's own file; there is nothing to move to superseded.
    (snaps / f'{DAY}.txt').write_text(SNAPSHOT + '012346;K;2026-11-01;2026-12-01;2026-10-01;2026-11-01;Company\n', encoding='utf-8')
    assert not (snaps / 'superseded').exists()
    assert results(register, folder, snaps)[7].status == 'PASS'
    # A ledger that matches neither file still fails.
    (snaps / '2026-11-21.txt').write_text(SNAPSHOT + '012346;K;2026-11-02;2026-12-01;2026-10-01;2026-11-01;Company\n', encoding='utf-8')
    assert results(register, folder, snaps)[7].status == 'FAIL'


def test_a_negative_alternatives_count_fails_and_a_register_dated_after_the_ledger_warns():
    assert status(v.check_alternatives_per_group([row('1', alternatives=-1), row('2', alternatives=-1)])) == 'FAIL'
    assert status(v.check_other_packages([row('1', alternatives=-1)], {'1': 2})) == 'FAIL'
    future = v.check_register_date([row(register_date='2026-11-24')], DAY)
    assert status(future) == 'WARN' and 'after the ledger date' in future.message and 'older' not in future.message


def test_read_rows_reads_only_files_named_yyyy_mm(tmp_path):
    line = json.dumps(row()) + '\n'
    for name in ('2026-11.jsonl', 'notes-11.jsonl', 'counts-2026-11.jsonl', '2026-11.jsonl.bak', '2026-1.jsonl'):
        (tmp_path / name).write_text(line, encoding='utf-8')
    assert len(ledger.read_rows(tmp_path)) == 1


# 9 counts agree with the ledger
def good_counts(rows, company='A'):
    """Complete counts rows for `rows`: a group row for each group and one company that lists every row."""
    groups = {r['group']: r['alternatives'] for r in rows if r['group']}
    out = [{'type': 'company', 'company': company, 'listed': len(rows), 'listed_human': len(rows), 'listed_vet': 0, 'on_market': 9, 'on_market_human': 9, 'on_market_vet': 0}]
    return out + [{'type': 'group', 'group': g, 'alternatives': a, 'listed': sum(r['group'] == g for r in rows), 'on_market': a + 1} for g, a in groups.items()]


def test_check_9_counts_agree_with_the_ledger():
    rows = [row('1', group='0042', alternatives=2), row('2', group='0042', alternatives=2), row('3', group='', alternatives=None, impact='nogroup')]
    same = good_counts(rows)
    assert status(v.check_counts(rows, same)) == 'PASS'
    different = [dict(r, alternatives=3, on_market=4) if r['type'] == 'group' else r for r in same]
    failing = v.check_counts(rows, different)
    assert status(failing) == 'FAIL' and 'group 0042: ledger 2, counts 3' in failing.message
    assert status(v.check_counts(rows, [])) == 'FAIL'  # a group of the ledger is missing in the counts
    assert status(v.check_counts(rows, same + [{'type': 'group', 'group': '0099', 'alternatives': 0, 'listed': 0, 'on_market': 1}])) == 'FAIL'  # an extra group
    assert status(v.check_counts(rows, None)) == 'FAIL'  # no counts file for the day


def test_check_9_compares_alternatives_with_on_market_and_the_company_parts():
    rows = [row('1', group='0042', alternatives=2), row('2', group='0042', alternatives=2), row('3', group='', alternatives=None, impact='nogroup')]
    same = good_counts(rows)

    def change(index, **fields):
        return [dict(r, **fields) if i == index else r for i, r in enumerate(same)]
    group = 1  # same[0] is the company
    too_many = v.check_counts(rows, change(group, on_market=1))  # 2 alternatives cannot be more than the 1 package on the market
    assert status(too_many) == 'FAIL' and 'alternatives 2 against on_market 1' in too_many.message
    assert status(v.check_counts(rows, change(group, on_market=None))) == 'FAIL'
    assert status(v.check_counts(rows, change(group, listed=1))) == 'PASS'  # `listed` is check 12's, a warning only
    assert status(v.check_counts(rows, change(0, listed_vet=1))) == 'FAIL'  # 3 listed is not 3 human + 1 vet
    assert status(v.check_counts(rows, change(0, on_market_human=8))) == 'FAIL'
    assert status(v.check_counts(rows, change(0, listed_human=None))) == 'FAIL'
    assert status(v.check_counts(rows, same + [dict(same[0], company='B', listed=0, listed_human=0)])) == 'PASS'


# 12 the counts list what the ledger lists (WARN only)
def test_check_12_warns_and_never_fails():
    rows = [row('1', group='0042', alternatives=2), row('2', group='0042', alternatives=2), row('3', group='', alternatives=None, impact='nogroup')]
    same = good_counts(rows)
    assert status(v.check_counts_listed(rows, same)) == 'PASS'
    assert status(v.check_counts_listed(rows, None)) == 'SKIP'
    fewer_in_group = v.check_counts_listed(rows, [dict(r, listed=1) if r['type'] == 'group' else r for r in same])
    assert status(fewer_in_group) == 'WARN' and 'group 0042: ledger 2, counts 1' in fewer_in_group.message
    assert status(v.check_counts_listed(rows, [dict(r, listed=None) if r['type'] == 'group' else r for r in same])) == 'WARN'
    # A holder-less VNR is left out of the companies: 3 rows, 2 listed by companies.
    no_holder = v.check_counts_listed(rows, [dict(r, listed=2, listed_human=2) if r['type'] == 'company' else r for r in same])
    assert status(no_holder) == 'WARN' and 'the companies list 2 packages, the ledger has 3 rows' in no_holder.message
    # Two companies that list the same rows twice are also a difference.
    assert status(v.check_counts_listed(rows, same + [dict(same[0], company='B')])) == 'WARN'


def test_run_fails_check_9_when_the_counts_file_is_missing_or_different(tmp_path, monkeypatch):
    register, folder, snaps = setup(tmp_path, monkeypatch)
    path = folder / 'counts' / f'{DAY}.jsonl'
    text = path.read_text(encoding='utf-8')
    path.write_text(text.replace('"alternatives":1,', '"alternatives":5,'), encoding='utf-8')
    assert results(register, folder, snaps)[9].status == 'FAIL'
    path.unlink()
    assert results(register, folder, snaps)[9].status == 'FAIL'
    path.write_text(text, encoding='utf-8')
    assert results(register, folder, snaps)[9].status == 'PASS'


def test_check_9_fails_on_two_counts_rows_for_one_group():
    rows = [row('1', group='0042', alternatives=2)]
    two = good_counts(rows) + [{'type': 'group', 'group': '0042', 'alternatives': 3, 'listed': 1, 'on_market': 4}]
    failing = v.check_counts(rows, two)
    assert status(failing) == 'FAIL' and 'group 0042 has 2 counts rows' in failing.message


def test_validation_after_midnight_checks_the_newest_ledger_day(tmp_path, monkeypatch, capsys):
    register, folder, snaps = setup(tmp_path, monkeypatch)  # ledger and counts finished for DAY (23 Nov)
    monkeypatch.setattr(v, 'LEDGER', folder)
    monkeypatch.setattr(v, 'ROOT', tmp_path)
    monkeypatch.setattr(v, 'helsinki_today', lambda: '2026-11-24')  # the clock has passed midnight since the two steps
    assert v.main(['--register', str(register)]) == 0
    assert f'Daily validation for {DAY}: 0 failed' in capsys.readouterr().out
    # An explicit day with no rows still fails.
    assert v.main(['--day', '2026-11-24', '--register', str(register)]) == 1


# 10 the newest ledger day is today
def test_check_10_newest_ledger_day_is_today():
    assert status(v.check_ledger_current('2026-11-23', '2026-11-23')) == 'PASS'
    one = v.check_ledger_current('2026-11-22', '2026-11-23')
    assert status(one) == 'WARN' and '1 day before today' in one.message  # a later run of the day writes the rows; a run past midnight looks the same
    two = v.check_ledger_current('2026-11-21', '2026-11-23')
    assert status(two) == 'FAIL' and '2 days before today' in two.message and 'did not write' in two.message
    assert status(v.check_ledger_current('2026-11-01', '2026-11-23')) == 'FAIL'
    assert status(v.check_ledger_current('2026-11-24', '2026-11-23')) == 'WARN'  # a newest day in the future is a clock problem, not a missing day


def test_run_adds_check_10_only_when_today_is_given(tmp_path, monkeypatch):
    register, folder, snaps = setup(tmp_path, monkeypatch)
    assert 10 not in results(register, folder, snaps)  # an explicit --day is a deliberate look at one day
    assert results(register, folder, snaps, today=DAY)[10].status == 'PASS'
    assert results(register, folder, snaps, today='2026-11-24')[10].status == 'WARN'
    assert results(register, folder, snaps, today='2026-11-25')[10].status == 'FAIL'


def test_main_passes_today_only_without_an_explicit_day(monkeypatch):
    seen = []
    monkeypatch.setattr(v, 'run', lambda day, **kw: seen.append(kw.get('today')) or [v.Result(1, 'x', 'PASS', 'ok')])
    monkeypatch.setattr(v, 'helsinki_today', lambda: '2026-11-24')
    monkeypatch.setattr(v, 'read_rows', lambda *a, **k: [row()])
    v.main([])
    v.main(['--day', DAY])
    assert seen == ['2026-11-24', None]


def test_a_ledger_step_that_failed_two_days_ago_is_reported_by_main(tmp_path, monkeypatch, capsys):
    register, folder, snaps = setup(tmp_path, monkeypatch)  # the ledger has only DAY (23 Nov)
    monkeypatch.setattr(v, 'LEDGER', folder)
    monkeypatch.setattr(v, 'ROOT', tmp_path)
    monkeypatch.setattr(v, 'helsinki_today', lambda: '2026-11-25')  # the ledger steps of 24 and 25 Nov wrote nothing
    assert v.main(['--register', str(register)]) == 1
    assert '::error::check 10 FAIL' in capsys.readouterr().out


# 11 impact follows from group and alternatives
def test_check_11_impact_follows_from_group_and_alternatives():
    good = [row('1', group='0042', alternatives=2, impact='substitute'), row('2', group='0043', alternatives=0, impact='no_alternative'),
            row('3', group='', alternatives=None, impact='nogroup'), row('4', group='', alternatives=None, impact='vet'),
            row('5', group='0044', alternatives=3, impact='vet'), row('6', group='0043', alternatives=0, impact='critical', date='2026-11-24')]
    assert status(v.check_impact_matches_group(good)) == 'PASS'  # vet holds whatever the group; the old name critical is no_alternative
    for bad in (row('1', group='0042', alternatives=0, impact='substitute'), row('1', group='0042', alternatives=2, impact='no_alternative'),
                row('1', group='0042', alternatives=2, impact='nogroup'), row('1', group='', alternatives=None, impact='substitute'),
                row('1', group='', alternatives=None, impact='no_alternative'), row('1', group='0042', alternatives=1, impact='critical')):
        assert status(v.check_impact_matches_group([bad])) == 'FAIL', bad
    wrong = v.check_impact_matches_group([row('7', group='0042', alternatives=0, impact='substitute')])
    assert '7 (impact substitute' in wrong.message and 'expected no_alternative' in wrong.message
    # What checks 2 and 8 report is not reported twice.
    assert status(v.check_impact_matches_group([row('1', group='0042', alternatives=None, impact='substitute'), row('2', impact='unknown')])) == 'PASS'


def test_the_checks_pass_on_every_real_ledger_day_in_the_repository():
    folder = Path(__file__).resolve().parents[1] / 'data/ledger'
    rows = ledger.read_rows(folder, canonical=False)
    # Pinned to the days that existed when the checks were written. A later bad day is the job of the daily alert; it must not turn the CI of an unrelated change red.
    days = sorted(d for d in {r['date'] for r in rows} if d <= '2026-11-26')
    assert days
    for day in days:
        day_rows = [r for r in rows if r['date'] == day]
        assert status(v.check_impact_matches_group(day_rows)) == 'PASS', day
        assert status(v.check_alternatives_per_group(day_rows)) == 'PASS', day
        counts_path = folder / 'counts' / f'{day}.jsonl'
        if counts_path.exists():  # counts exist from 25 Nov 2026
            counts_rows = [json.loads(line) for line in counts_path.read_text(encoding='utf-8').splitlines()]
            assert status(v.check_counts(day_rows, counts_rows)) == 'PASS', day
