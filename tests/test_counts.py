import json
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
    return register, tmp_path / 'ledger'


def read(folder):
    return [json.loads(line) for line in (folder / 'counts-2026-11.jsonl').read_text(encoding='utf-8').splitlines()]


def test_company_rows_count_listed_and_on_market_with_the_human_and_vet_split(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    assert counts.record(DAY, folder, register) == 4
    companies = [r for r in read(folder) if r['type'] == 'company']
    assert companies == [
        {'date': DAY, 'type': 'company', 'company': 'Alfa Oy', 'listed': 3, 'listed_human': 3, 'listed_vet': 0, 'on_market': 4, 'on_market_human': 4, 'on_market_vet': 0, 'register_date': DAY},
        {'date': DAY, 'type': 'company', 'company': 'Gamma Oy', 'listed': 1, 'listed_human': 0, 'listed_vet': 1, 'on_market': 2, 'on_market_human': 0, 'on_market_vet': 2, 'register_date': DAY}]
    # Beta Oy has no listed package, so it has no company row (it still counts as a holder of alternatives in group 0042).
    assert all(r['company'] != 'Beta Oy' for r in companies)


def test_group_rows_use_the_repo_rules_for_market_and_alternatives(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    counts.record(DAY, folder, register)
    groups = {r['group']: r for r in read(folder) if r['type'] == 'group'}
    assert sorted(groups) == ['0042', '0043']  # no row for the empty group of the veterinary package
    # Group 0042: 012346 and 012348 are alternatives (on the market, not short, not listed); 012349 is not on the market.
    assert groups['0042'] == {'date': DAY, 'type': 'group', 'group': '0042', 'on_market': 3, 'listed': 1, 'alternatives': 2, 'distinct_alternative_holders': 2, 'register_date': DAY}
    # Group 0043: both packages are listed, so none is an alternative.
    assert groups['0043'] == {'date': DAY, 'type': 'group', 'group': '0043', 'on_market': 2, 'listed': 2, 'alternatives': 0, 'distinct_alternative_holders': 0, 'register_date': DAY}


def test_group_alternatives_equal_the_value_the_ledger_writes(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(ledger, 'ROOT', tmp_path)
    # The ledger takes today's date for the register day; the counts take the day they are written for. They agree on the register's own day.
    day = build.helsinki_today()
    ledger.record(day, folder, register)
    counts.record(day, folder, register)
    by_group = {r['group']: r['alternatives'] for r in ledger.read_rows(folder) if r['group']}
    rows = [json.loads(line) for line in (folder / f'counts-{day[:7]}.jsonl').read_text(encoding='utf-8').splitlines()]
    assert {r['group']: r['alternatives'] for r in rows if r['type'] == 'group'} == by_group


def test_the_first_run_of_a_day_writes_and_later_runs_add_nothing(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    assert counts.record(DAY, folder, register) > 0
    before = (folder / 'counts-2026-11.jsonl').read_bytes()
    assert counts.record(DAY, folder, register) == 0
    register.write_text(REGISTER.replace('Alfa Oy', 'Changed Oy'), encoding='utf-8')
    assert counts.record(DAY, folder, register) == 0
    assert (folder / 'counts-2026-11.jsonl').read_bytes() == before


def test_a_new_day_appends_a_new_month_starts_a_new_file_and_the_ledger_files_are_not_touched(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    counts.record(DAY, folder, register)
    first = (folder / 'counts-2026-11.jsonl').read_bytes()
    counts.record('2026-11-24', folder, register)
    assert (folder / 'counts-2026-11.jsonl').read_bytes().startswith(first)
    assert {r['date'] for r in read(folder)} == {DAY, '2026-11-24'}
    counts.record('2026-12-01', folder, register)
    assert sorted(p.name for p in folder.iterdir()) == ['counts-2026-11.jsonl', 'counts-2026-12.jsonl']
    # The ledger reader does not read the counts files.
    assert ledger.read_rows(folder) == []


def test_rows_are_deterministic_and_small(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    counts.record(DAY, folder, register)
    again = tmp_path / 'again'
    counts.record(DAY, again, register)
    assert (folder / 'counts-2026-11.jsonl').read_bytes() == (again / 'counts-2026-11.jsonl').read_bytes()
    lines = (folder / 'counts-2026-11.jsonl').read_text(encoding='utf-8').splitlines()
    assert [json.loads(line)['type'] for line in lines] == ['company', 'company', 'group', 'group']  # companies by name, then groups by code
    assert max(len(line) for line in lines) < 300
