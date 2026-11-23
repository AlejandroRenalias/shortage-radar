import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import source_age
from source_age import STALE_DAYS, stale_reasons

SAT = 'Sat, 21 Nov 2026 10:00:00 GMT'


def test_the_limit_is_two_days_in_python_and_in_the_site_code():
    assert STALE_DAYS == 2
    assert re.search(r'const STALE_DAYS = 2;', (Path(__file__).resolve().parents[1] / 'site/lib.js').read_text(encoding='utf-8'))


def test_fresh_files_are_not_stale_including_exactly_two_days():
    meta = {'shortages_last_modified': SAT, 'register_date': '2026-11-21'}
    assert stale_reasons(meta, date(2026, 11, 21)) == []
    assert stale_reasons(meta, date(2026, 11, 23)) == []   # Saturday's file on Monday: two days, not more


def test_a_shortage_file_older_than_two_days_is_stale():
    meta = {'shortages_last_modified': SAT, 'register_date': '2026-11-23'}
    assert stale_reasons(meta, date(2026, 11, 24)) == [{'file': 'shortages', 'date': '2026-11-21', 'days': 3}]


def test_the_file_date_is_the_helsinki_day():
    # 22:30 GMT on 21 Nov is 00:30 on 22 Nov in Helsinki.
    meta = {'shortages_last_modified': 'Sat, 21 Nov 2026 22:30:00 GMT'}
    assert stale_reasons(meta, date(2026, 11, 24)) == []
    assert stale_reasons(meta, date(2026, 11, 25))[0]['date'] == '2026-11-22'


def test_an_old_register_is_stale_even_when_the_shortage_file_is_new():
    meta = {'shortages_last_modified': 'Mon, 23 Nov 2026 01:00:00 GMT', 'register_date': '2026-11-19'}
    assert stale_reasons(meta, date(2026, 11, 23)) == [{'file': 'register', 'date': '2026-11-19', 'days': 4}]


def test_both_files_can_be_stale_and_unknown_dates_are_not_stale():
    meta = {'shortages_last_modified': SAT, 'register_date': '2026-11-10'}
    assert [r['file'] for r in stale_reasons(meta, date(2026, 11, 30))] == ['shortages', 'register']
    assert stale_reasons({}, date(2026, 11, 30)) == []
    assert stale_reasons({'shortages_last_modified': 'not a date', 'register_date': 'x'}, date(2026, 11, 30)) == []
    assert stale_reasons({'shortages_last_modified': None}, date(2026, 11, 30)) == []


def run_main(monkeypatch, meta, today):
    monkeypatch.setattr(source_age, 'read_metadata', lambda: meta)
    monkeypatch.setattr(source_age, 'stale_reasons', lambda m, now=None: stale_reasons(m, today))
    return source_age.main()


def test_the_command_fails_visibly_when_a_file_is_stale(monkeypatch, capsys):
    assert run_main(monkeypatch, {'shortages_last_modified': SAT, 'register_date': '2026-11-01'}, date(2026, 11, 25)) == 1
    out = capsys.readouterr().out
    assert '::warning::' in out and 'shortage file' in out and 'basic register' in out


def test_unknown_dates_are_reported_separately_and_never_pass_as_fresh(monkeypatch, capsys, tmp_path):
    out_file = tmp_path / 'out'
    assert source_age.status({}, date(2026, 11, 22)) == 'unknown'
    # A stale file is evidence even when the other date is unknown; fresh needs both dates.
    assert source_age.status({'shortages_last_modified': SAT}, date(2026, 11, 30)) == 'stale'
    assert source_age.status({'shortages_last_modified': SAT, 'register_date': '2026-11-21'}, date(2026, 11, 22)) == 'fresh'
    monkeypatch.setenv('GITHUB_OUTPUT', str(out_file))
    for meta in ({}, {'shortages_last_modified': None, 'register_date': '2026-11-22'}, {'shortages_last_modified': SAT, 'register_date': 'bad'}):
        assert run_main(monkeypatch, meta, date(2026, 11, 22)) == 0
        out = capsys.readouterr().out
        assert 'unknown' in out and 'at most 2 days' not in out and 'status=unknown' in out
    assert set(out_file.read_text().split()) == {'status=unknown'}
    assert run_main(monkeypatch, {'shortages_last_modified': SAT}, date(2026, 11, 30)) == 1


def test_the_workflow_clears_the_stale_alert_only_on_fresh():
    text = (Path(__file__).resolve().parents[1] / '.github/workflows/archive.yml').read_text(encoding='utf-8')
    assert 'age: ${{ steps.age.outputs.status }}' in text
    assert '= stale ]; then PIPELINE=source-stale RESULT=failure' in text and '= fresh ]; then PIPELINE=source-stale RESULT=success' in text
    assert 'source-stale RESULT=${{' not in text       # no branch turns an unknown status into success


def test_the_command_passes_when_both_files_are_fresh(monkeypatch, capsys):
    assert run_main(monkeypatch, {'shortages_last_modified': SAT, 'register_date': '2026-11-21'}, date(2026, 11, 22)) == 0
    assert 'at most 2 days' in capsys.readouterr().out


def test_read_metadata_joins_both_files(tmp_path):
    (tmp_path / 'metadata.json').write_text('{"a": 1}', encoding='utf-8')
    assert source_age.read_metadata(tmp_path) == {'a': 1}
    (tmp_path / 'register-metadata.json').write_text('{"b": 2}', encoding='utf-8')
    assert source_age.read_metadata(tmp_path) == {'a': 1, 'b': 2}


def test_register_date_reads_the_run_date(tmp_path):
    path = tmp_path / 'r.xml'
    path.write_text('<Perusrekisteri><Versiotiedot><Ajopvm> 2026-11-23 </Ajopvm></Versiotiedot></Perusrekisteri>', encoding='utf-8')
    assert source_age.register_date(path) == '2026-11-23'
    path.write_text('<Perusrekisteri/>', encoding='utf-8')
    assert source_age.register_date(path) == ''
