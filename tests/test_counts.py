import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build
import counts
import ledger

# Group 0042: 012345 (listed, Alfa), 012346 (Alfa, on market, not short), 012348 (Beta, on market, not short), 012349 (Beta, not on market).
# Group 0043: 012350 (listed, Alfa, veterinary ATC is not used here: groups are human). 012351 listed in the file but flagged short too.
# 012347 has no group (Gamma, veterinary), listed. 012360 is a package of Gamma that is on the market and not listed.
REGISTER = '''<Perusrekisteri><Ajopvm>2026-11-23</Ajopvm>
  <Pakkaus Laakevalmiste-ref="p1"><VNR-numero>012345</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>1</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>
  <Pakkaus Laakevalmiste-ref="p1"><VNR-numero>012346</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>0</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>
  <Pakkaus Laakevalmiste-ref="p3"><VNR-numero>012348</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>0</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>
  <Pakkaus Laakevalmiste-ref="p3"><VNR-numero>012349</VNR-numero><Kaupanolo><Kaupan>0</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>0</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>
  <Pakkaus Laakevalmiste-ref="p4"><VNR-numero>012350</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>1</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>
  <Pakkaus Laakevalmiste-ref="p4"><VNR-numero>012351</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>1</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>
  <Pakkaus Laakevalmiste-ref="p2"><VNR-numero>012347</VNR-numero><VanhaVNR>099999</VanhaVNR><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo></Pakkaus>
  <Pakkaus Laakevalmiste-ref="p2"><VNR-numero>012360</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo></Pakkaus>
  <Laakevalmiste id="p1"><Kauppanimi>One</Kauppanimi><ATC-koodi id="N02" value="x"/><Myyntilupa><Haltija>Alfa Oy</Haltija></Myyntilupa><Substituutioryhma id="0042" value="0042"/></Laakevalmiste>
  <Laakevalmiste id="p3"><Kauppanimi>Two</Kauppanimi><ATC-koodi id="N02" value="x"/><Myyntilupa><Haltija>Beta  Oy</Haltija></Myyntilupa><Substituutioryhma id="0042" value="0042"/></Laakevalmiste>
  <Laakevalmiste id="p4"><Kauppanimi>Three</Kauppanimi><ATC-koodi id="N02" value="x"/><Myyntilupa><Haltija>Alfa Oy</Haltija></Myyntilupa><Substituutioryhma id="0043" value="0043"/></Laakevalmiste>
  <Laakevalmiste id="p2"><Kauppanimi>Vet</Kauppanimi><ATC-koodi id="QN02" value="x"/><Myyntilupa><Haltija>Gamma Oy</Haltija></Myyntilupa><Substituutioryhma/></Laakevalmiste>
</Perusrekisteri>'''
HEADER = 'NordicArticleNumber;Valid;UnavailableFrom;EndingDate;DateOfTheNotification;Updated;Company\n'
# 099999 is the old VNR of 012347; the file lists 012345, 012350, 012351 and the old number.
SNAPSHOT = HEADER + ''.join(f'{v};K;2026-11-01;2026-12-01;2026-10-01;2026-11-01;Company\n' for v in ('012345', '012350', '012351', '099999'))
DAY = '2026-11-23'


def setup(tmp_path, monkeypatch):
    (tmp_path / 'data/snapshots').mkdir(parents=True)
    (tmp_path / 'data/snapshots/2026-11-22.txt').write_text(SNAPSHOT, encoding='utf-8')
    register = tmp_path / 'register.xml'
    register.write_text(REGISTER, encoding='utf-8')
    monkeypatch.setattr(build, 'ROOT', tmp_path)
    monkeypatch.setattr(counts, 'ROOT', tmp_path)
    monkeypatch.setattr(ledger, 'ROOT', tmp_path)
    return register, tmp_path / 'ledger'


def rec(day, folder, register, **kw):
    """The ledger rows of the day first (the job does the same), then the counts."""
    ledger.record(day, folder, register)
    return counts.record(day, folder, register, **kw)


def day_file(folder, day=DAY):
    return folder / 'counts' / f'{day}.jsonl'


def read(folder, day=DAY):
    return [json.loads(line) for line in day_file(folder, day).read_text(encoding='utf-8').splitlines()]


def test_company_rows_count_listed_and_on_market_with_the_human_and_vet_split(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    assert rec(DAY, folder, register) == 4
    companies = [r for r in read(folder) if r['type'] == 'company']
    assert companies == [
        {'date': DAY, 'type': 'company', 'company': 'Alfa Oy', 'listed': 3, 'listed_human': 3, 'listed_vet': 0, 'on_market': 4, 'on_market_human': 4, 'on_market_vet': 0, 'register_date': DAY},
        {'date': DAY, 'type': 'company', 'company': 'Gamma Oy', 'listed': 1, 'listed_human': 0, 'listed_vet': 1, 'on_market': 2, 'on_market_human': 0, 'on_market_vet': 2, 'register_date': DAY}]
    # Beta Oy has no listed package, so it has no company row (it still counts as a holder of alternatives in group 0042).
    assert all(r['company'] != 'Beta Oy' for r in companies)


def test_group_rows_use_the_repo_rules_for_market_and_alternatives(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    rec(DAY, folder, register)
    groups = {r['group']: r for r in read(folder) if r['type'] == 'group'}
    assert sorted(groups) == ['0042', '0043']  # no row for the empty group of the veterinary package
    # Group 0042: 012346 and 012348 are alternatives (on the market, not short, not listed); 012349 is not on the market.
    assert groups['0042'] == {'date': DAY, 'type': 'group', 'group': '0042', 'on_market': 3, 'listed': 1, 'alternatives': 2, 'distinct_alternative_holders': 2, 'register_date': DAY}
    # Group 0043: both packages are listed, so none is an alternative.
    assert groups['0043'] == {'date': DAY, 'type': 'group', 'group': '0043', 'on_market': 2, 'listed': 2, 'alternatives': 0, 'distinct_alternative_holders': 0, 'register_date': DAY}


def group_alternatives(folder, day):
    ledger_values = {r['group']: r['alternatives'] for r in ledger.read_rows(folder) if r['group'] and r['date'] == day}
    counts_values = {r['group']: r['alternatives'] for r in read(folder, day) if r['type'] == 'group'}
    return ledger_values, counts_values


def test_group_alternatives_equal_the_value_the_ledger_writes(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    day = build.helsinki_today()  # the ledger takes today's date for the register day; they agree on it
    rec(day, folder, register)
    ledger_values, counts_values = group_alternatives(folder, day)
    assert counts_values == ledger_values and counts_values['0042'] == 2


def test_a_vnr_with_two_register_records_gives_the_same_alternatives_as_the_ledger(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    record = '  <Pakkaus Laakevalmiste-ref="p1"><VNR-numero>012346</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>%s</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>\n'
    # 012346 is written twice: first flagged short, then available.
    available = record % '0'
    assert available in REGISTER
    text = REGISTER.replace(available, (record % '1') + available, 1)
    register.write_text(text, encoding='utf-8')
    day = build.helsinki_today()
    rec(day, folder, register)
    ledger_values, counts_values = group_alternatives(folder, day)
    assert counts_values == ledger_values and counts_values['0042'] == 2
    row = next(r for r in read(folder, day) if r['type'] == 'group' and r['group'] == '0042')
    assert (row['on_market'], row['listed']) == (3, 1)  # a VNR counts once


def test_the_first_run_of_a_day_writes_and_an_existing_day_file_is_never_touched(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    assert rec(DAY, folder, register) > 0
    before = day_file(folder).read_bytes()
    assert counts.record(DAY, folder, register) == 0
    # A different register, a different shortage file, or damage to the ledger does not matter: the day has its file and nothing reads the inputs.
    register.write_text(REGISTER.replace('Alfa Oy', 'Changed Oy'), encoding='utf-8')
    (tmp_path / 'data/snapshots/2026-11-22.txt').write_text(SNAPSHOT + '012346;K;2026-11-01;2026-12-01;2026-10-01;2026-11-01;Company\n', encoding='utf-8')
    assert counts.record(DAY, folder, register) == 0
    assert day_file(folder).read_bytes() == before


def test_one_file_for_each_day_and_the_ledger_files_are_not_touched(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    rec(DAY, folder, register)
    rec('2026-11-24', folder, register)
    rec('2026-12-01', folder, register)
    assert sorted(p.name for p in (folder / 'counts').iterdir()) == [f'{DAY}.jsonl', '2026-11-24.jsonl', '2026-12-01.jsonl']
    assert sorted(p.name for p in folder.iterdir() if p.is_file()) == ['2026-11.jsonl', '2026-12.jsonl']
    assert set(counts.read_days(folder)) == {DAY, '2026-11-24', '2026-12-01'}
    # The ledger reader reads no counts rows.
    assert all('type' not in r for r in ledger.read_rows(folder)) and {r['date'] for r in ledger.read_rows(folder)} == {DAY, '2026-11-24', '2026-12-01'}


def test_rows_are_deterministic_and_small(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    rec(DAY, folder, register)
    again = tmp_path / 'again'
    rec(DAY, again, register)
    assert day_file(folder).read_bytes() == day_file(again).read_bytes()
    lines = day_file(folder).read_text(encoding='utf-8').splitlines()
    assert [json.loads(line)['type'] for line in lines] == ['company', 'company', 'group', 'group']  # companies by name, then groups by code
    assert max(len(line) for line in lines) < 300


def test_a_crash_while_writing_leaves_no_day_file_and_the_next_run_works_and_removes_the_temp_file(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    ledger.record(DAY, folder, register)

    def crash(source, target):
        raise OSError('disk full')
    with monkeypatch.context() as m:
        m.setattr(counts.os, 'replace', crash)
        try:
            counts.record(DAY, folder, register)
            raise AssertionError('the crash must show')
        except OSError:
            pass
    assert not day_file(folder).exists()
    assert [p.name for p in (folder / 'counts').iterdir()] == [f'{counts.TEMP_PREFIX}{DAY}']
    assert counts.read_days(folder) == {}  # the temporary file is not a day
    assert counts.record(DAY, folder, register) > 0
    assert [p.name for p in (folder / 'counts').iterdir()] == [f'{DAY}.jsonl']
    counts.check_file(day_file(folder))


def test_a_temporary_file_cut_inside_a_utf8_character_is_ignored(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    ledger.record(DAY, folder, register)
    (folder / 'counts').mkdir()
    cut = '{"company":"Ålandsbanken Ab","date":"2026-11-23"'.encode('utf-8')
    leftover = folder / 'counts' / f'{counts.TEMP_PREFIX}{DAY}'
    leftover.write_bytes(cut[:cut.index('Å'.encode('utf-8')) + 1])  # only the first byte of the two-byte letter
    assert counts.read_days(folder) == {}  # nothing reads it, so nothing crashes
    ledger.record('2026-11-24', folder, register)
    (folder / 'counts' / f'{counts.TEMP_PREFIX}2026-11-24').write_bytes(b'\xc3')
    assert counts.record(DAY, folder, register) > 0
    assert sorted(p.name for p in (folder / 'counts').iterdir()) == [f'{DAY}.jsonl']
    assert counts.record('2026-11-24', folder, register) > 0


def test_check_file_rejects_an_incomplete_or_foreign_file(tmp_path):
    ok = tmp_path / '2026-11-23.jsonl'
    ok.write_text('{"date":"2026-11-23","type":"group"}\n', encoding='utf-8')
    counts.check_file(ok)
    assert counts.main(['--check', str(ok)]) == 0
    bad = ('{"date":"2026-11-23","type":"gr', '{"date":"2026-11-23","type":"group"}', '{"date":"2026-11-23"}\n', '{"date":"2026-11-24","type":"group"}\n', '', '[1]\n')
    for text in bad:
        ok.write_text(text, encoding='utf-8')
        assert counts.main(['--check', str(ok)]) == 1
    ok.write_bytes('{"date":"2026-11-23","type":"group","company":"Å"}\n'.encode('utf-8')[:-8] + b'\xc3\n')
    assert counts.main(['--check', str(ok)]) == 1  # not UTF-8


def test_counts_use_the_inputs_of_the_ledger_rows_and_refuse_others(tmp_path, monkeypatch, capsys):
    register, folder = setup(tmp_path, monkeypatch)
    ledger.record(DAY, folder, register)
    register.write_text(REGISTER.replace('<Ajopvm>2026-11-23', '<Ajopvm>2026-11-24').replace('Alfa Oy', 'New Oy'), encoding='utf-8')
    try:
        counts.record(DAY, folder, register)
        raise AssertionError('a newer register must be refused')
    except counts.CountsInputError as error:
        assert 'register_date 2026-11-23' in str(error) and ledger.read_rows(folder)[0]['register_sha256'] in str(error)
    assert not day_file(folder).exists()
    # The same-day retry cannot write with a changed shortage file either, and a day with no ledger rows has no counts.
    register.write_text(REGISTER, encoding='utf-8')
    (tmp_path / 'data/snapshots/2026-11-22.txt').write_text(SNAPSHOT + '012346;K;2026-11-01;2026-12-01;2026-10-01;2026-11-01;Company\n', encoding='utf-8')
    for day in (DAY, '2026-11-30'):
        try:
            counts.record(day, folder, register)
            raise AssertionError('changed inputs must be refused')
        except counts.CountsInputError:
            pass
    (tmp_path / 'data/snapshots/2026-11-22.txt').write_text(SNAPSHOT, encoding='utf-8')
    assert counts.record(DAY, folder, register) > 0
    assert {r['register_date'] for r in read(folder)} == {'2026-11-23'}


def test_main_reports_refused_inputs_in_the_log(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(counts, 'record', lambda *a, **k: (_ for _ in ()).throw(counts.CountsInputError('no ledger rows')))
    assert counts.main([]) == 1 and '::error::Daily counts not written: no ledger rows' in capsys.readouterr().out


def find_bash():
    """A bash that can run the workflow's shell lines: on Windows Git Bash (found next to git), never the WSL launcher in System32 or WindowsApps."""
    candidates = []
    git_path = shutil.which('git')
    if git_path:
        root = Path(git_path).resolve().parent.parent
        candidates += [root / 'bin/bash.exe', root.parent / 'bin/bash.exe', root / 'usr/bin/bash.exe']
    candidates += [Path(p) for p in (shutil.which('bash'),) if p]
    for path in candidates:
        if path.exists() and not any(part.lower() in ('system32', 'windowsapps') for part in path.parts):
            try:
                if subprocess.run([str(path), '-c', 'echo ok'], capture_output=True, text=True, timeout=30).stdout.strip() == 'ok':
                    return str(path)
            except (OSError, subprocess.SubprocessError):
                continue
    return None


def guard_script():
    text = (Path(__file__).resolve().parents[1] / '.github/workflows/archive.yml').read_text(encoding='utf-8')
    start, end = text.index('# counts guard start'), text.index('# counts guard end')
    body = '\n'.join(line.strip() for line in text[start:end].splitlines())
    return body.replace('python scripts/counts.py', f'python "{(Path(__file__).resolve().parents[1] / "scripts/counts.py").as_posix()}"')


def git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


GOOD = '{"date":"%s","type":"group"}\n'


def test_the_workflow_guard_restores_or_removes_invalid_files_and_never_stages_a_deletion(tmp_path):
    bash = find_bash()
    if not bash or not shutil.which('git'):
        import pytest
        pytest.skip('needs a working bash (Git Bash on Windows; the WSL launcher in System32 is not used) and git')
    git(tmp_path, 'init', '-q')
    git(tmp_path, 'config', 'user.email', 'a@b.c')
    git(tmp_path, 'config', 'user.name', 'a')
    folder = tmp_path / 'data/ledger/counts'
    folder.mkdir(parents=True)
    (folder / '2026-11-24.jsonl').write_text(GOOD % '2026-11-24', encoding='utf-8')
    (folder / '2026-11-25.jsonl').write_text(GOOD % '2026-11-25', encoding='utf-8')
    git(tmp_path, 'add', '-A')
    git(tmp_path, 'commit', '-q', '-m', 'base')
    # A committed day deleted, a committed day rewritten with a cut line, a new complete day, a new broken day, a new day cut in a character, a temporary file.
    (folder / '2026-11-24.jsonl').unlink()
    (folder / '2026-11-25.jsonl').write_text('{"date":"2026-11-25","ty', encoding='utf-8')
    (folder / '2026-11-26.jsonl').write_text(GOOD % '2026-11-26', encoding='utf-8')
    (folder / '2026-11-27.jsonl').write_text('{"date":"2026-11-27","type":"group"}', encoding='utf-8')
    (folder / '2026-11-28.jsonl').write_bytes(b'{"date":"2026-11-28","type":"group","company":"\xc3\n')
    (folder / '.tmp-2026-11-29').write_text('x', encoding='utf-8')
    script = guard_script() + '\ngit add data/ledger\n'
    run = subprocess.run([bash, '-c', script], cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    staged = dict(line.split('\t')[::-1] for line in git(tmp_path, 'diff', '--cached', '--name-status').splitlines())
    assert staged == {'data/ledger/counts/2026-11-26.jsonl': 'A'}  # only the good new day; no deletion, no change to a committed day
    assert (folder / '2026-11-24.jsonl').read_text(encoding='utf-8') == GOOD % '2026-11-24'
    assert (folder / '2026-11-25.jsonl').read_text(encoding='utf-8') == GOOD % '2026-11-25'
    assert sorted(p.name for p in folder.iterdir()) == ['2026-11-24.jsonl', '2026-11-25.jsonl', '2026-11-26.jsonl']


def old_vnr_register(extra=''):
    """The reviewer's fixture: 099998 is the old VNR of 012345; the register has two rows for 012345, the first with the old VNR and short, the second
    without it and available."""
    first = '<Pakkaus Laakevalmiste-ref="p1"><VNR-numero>012345</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>1</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>'
    assert first in REGISTER
    rows = ('<Pakkaus Laakevalmiste-ref="p1"><VNR-numero>012345</VNR-numero><VanhaVNR>099998</VanhaVNR><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>1</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>\n'
            '  <Pakkaus Laakevalmiste-ref="p1"><VNR-numero>012345</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>0</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>')
    return REGISTER.replace(first, rows, 1).replace('  <Laakevalmiste id="p1">', extra + '  <Laakevalmiste id="p1">', 1)


def test_a_listed_package_resolved_through_its_old_vnr_gives_the_same_alternatives_as_the_ledger(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    register.write_text(old_vnr_register(), encoding='utf-8')
    (tmp_path / 'data/snapshots/2026-11-22.txt').write_text(HEADER + '099998;K;2026-11-01;2026-12-01;2026-10-01;2026-11-01;Company\n', encoding='utf-8')
    day = build.helsinki_today()
    rec(day, folder, register)
    ledger_values, counts_values = group_alternatives(folder, day)
    assert counts_values == ledger_values == {'0042': 2}  # the ledger's number; counts used to say 3


def test_a_short_duplicate_of_a_vnr_adds_no_holder(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    short_other = ('  <Pakkaus Laakevalmiste-ref="p5"><VNR-numero>012346</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>1</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>\n'
                   '  <Laakevalmiste id="p5"><Kauppanimi>Five</Kauppanimi><ATC-koodi id="N02" value="x"/><Myyntilupa><Haltija>Delta Oy</Haltija></Myyntilupa><Substituutioryhma id="0042" value="0042"/></Laakevalmiste>\n')
    register.write_text(REGISTER.replace('  <Laakevalmiste id="p1">', short_other + '  <Laakevalmiste id="p1">', 1), encoding='utf-8')
    day = build.helsinki_today()
    rec(day, folder, register)
    row = next(r for r in read(folder, day) if r['type'] == 'group' and r['group'] == '0042')
    assert (row['alternatives'], row['distinct_alternative_holders']) == (2, 2)
    ledger_values, counts_values = group_alternatives(folder, day)
    assert ledger_values == counts_values


def test_counts_use_the_newest_ledger_day_not_the_clock(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    ledger.record('2026-11-23', folder, register)  # written at 23:59:59 Helsinki time
    assert not hasattr(counts, 'datetime')  # the counts step reads no clock: at 00:00:01 it still counts 23 Nov
    assert counts.record(None, folder, register) > 0
    assert sorted(p.name for p in (folder / 'counts').iterdir()) == ['2026-11-23.jsonl']
    ledger.record('2026-11-24', folder, register)
    assert counts.record(folder=folder, register_path=register) > 0
    assert sorted(p.name for p in (folder / 'counts').iterdir()) == ['2026-11-23.jsonl', '2026-11-24.jsonl']
    try:
        counts.record(folder=tmp_path / 'empty', register_path=register)
        raise AssertionError('no ledger, no counts')
    except counts.CountsInputError:
        pass


def test_counts_take_alternatives_from_the_ledger_rows_even_when_the_ledger_clock_passed_midnight(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    # 012346 enters the market on 26 Nov. The ledger of 25 Nov joins the register after midnight (clock: 26 Nov), so it counts 012346; the counts of
    # 25 Nov must not count again with the date 25 Nov.
    register.write_text(REGISTER.replace('<VNR-numero>012346</VNR-numero><Kaupanolo><Kaupan>1</Kaupan>', '<VNR-numero>012346</VNR-numero><Kaupanolo><Kaupan>1</Kaupan><Kauppaantulopaiva>2026-11-26</Kauppaantulopaiva>', 1), encoding='utf-8')
    monkeypatch.setattr(build, 'helsinki_today', lambda: '2026-11-26')
    ledger.record('2026-11-25', folder, register)
    assert counts.record(None, folder, register) > 0
    ledger_values, counts_values = group_alternatives(folder, '2026-11-25')
    assert ledger_values == counts_values and counts_values['0042'] == 2  # counting again with the date 25 Nov would give 1


def test_a_current_package_of_a_listed_old_vnr_adds_no_holder(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    # The reviewer's fixture with the available duplicate of 012345 assigned to another holder.
    delta = ('  <Pakkaus Laakevalmiste-ref="p5"><VNR-numero>012345</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>0</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>\n'
             '  <Laakevalmiste id="p5"><Kauppanimi>Five</Kauppanimi><ATC-koodi id="N02" value="x"/><Myyntilupa><Haltija>Delta Oy</Haltija></Myyntilupa><Substituutioryhma id="0042" value="0042"/></Laakevalmiste>\n')
    register.write_text(old_vnr_register(delta), encoding='utf-8')
    (tmp_path / 'data/snapshots/2026-11-22.txt').write_text(HEADER + '099998;K;2026-11-01;2026-12-01;2026-10-01;2026-11-01;Company\n', encoding='utf-8')
    day = build.helsinki_today()
    rec(day, folder, register)
    row = next(r for r in read(folder, day) if r['type'] == 'group' and r['group'] == '0042')
    assert (row['alternatives'], row['distinct_alternative_holders']) == (2, 2)
    ledger_values, counts_values = group_alternatives(folder, day)
    assert ledger_values == counts_values
