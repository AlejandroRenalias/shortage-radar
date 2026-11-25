import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build
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
    ledger.record(DAY, tmp_path / 'ledger', register)
    return register, tmp_path / 'ledger', tmp_path / 'data/snapshots'


def results(register, folder, snaps, **kw):
    return {r.number: r for r in v.run(DAY, folder, register, snaps, **kw)}


def test_run_passes_on_a_ledger_written_by_the_ledger_script(tmp_path, monkeypatch):
    register, folder, snaps = setup(tmp_path, monkeypatch)
    found = results(register, folder, snaps)
    assert {n: r.status for n, r in found.items()} == dict.fromkeys(range(1, 9), 'PASS')


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
    assert text.index('python scripts/ledger.py') < text.index('python scripts/validate_daily.py') < text.index('name: Commit changes')
    assert 'python scripts/counts.py' in text and 'PIPELINE=data-validation RESULT=failure' in text and 'PIPELINE=data-validation RESULT=success' in text
    from pipeline_alert import MEANING
    assert 'data-validation' in MEANING
