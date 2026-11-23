import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build
import ledger

REGISTER = '''<Perusrekisteri><Ajopvm>2026-11-23</Ajopvm>
  <Pakkaus Laakevalmiste-ref="p1"><VNR-numero>012345</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>1</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>
  <Pakkaus Laakevalmiste-ref="p1"><VNR-numero>012346</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>0</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>
  <Pakkaus Laakevalmiste-ref="p2"><VNR-numero>012347</VNR-numero></Pakkaus>
  <Laakevalmiste id="p1"><Kauppanimi>Example</Kauppanimi><Substituutioryhma id="0042" value="0042"/></Laakevalmiste>
  <Laakevalmiste id="p2"><Kauppanimi>Alone</Kauppanimi><Substituutioryhma/></Laakevalmiste>
</Perusrekisteri>'''
SNAPSHOT = 'NordicArticleNumber;Valid;UnavailableFrom;EndingDate;DateOfTheNotification;Updated;Company\n' + ''.join(
    f'{v};K;2026-11-01;2026-12-01;2026-10-01;2026-11-01;Company\n' for v in ('012345', '012347'))


def setup(tmp_path, monkeypatch):
    (tmp_path / 'data/snapshots').mkdir(parents=True)
    (tmp_path / 'data/snapshots/2026-11-22.txt').write_text(SNAPSHOT, encoding='utf-8')
    register = tmp_path / 'register.xml'
    register.write_text(REGISTER, encoding='utf-8')
    monkeypatch.setattr(build, 'ROOT', tmp_path)
    monkeypatch.setattr(ledger, 'ROOT', tmp_path)
    return register, tmp_path / 'ledger'


def read(folder, name):
    return [json.loads(line) for line in (folder / name).read_text(encoding='utf-8').splitlines()]


def test_rows_carry_group_impact_alternatives_register_date_and_hashes(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    assert ledger.record('2026-11-23', folder, register) == 2
    first, second = read(folder, '2026-11.jsonl')
    assert first == {'date': '2026-11-23', 'vnr': '012345', 'group': '0042', 'impact': 'substitute', 'alternatives': 1, 'register_date': '2026-11-23',
                     'shortages_sha256': ledger.sha256(tmp_path / 'data/snapshots/2026-11-22.txt'), 'register_sha256': ledger.sha256(register)}
    assert (second['vnr'], second['group'], second['impact'], second['alternatives']) == ('012347', '', 'nogroup', None)


def test_second_run_on_the_same_day_adds_no_rows(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    ledger.record('2026-11-23', folder, register)
    before = (folder / '2026-11.jsonl').read_bytes()
    assert ledger.record('2026-11-23', folder, register) == 0
    assert (folder / '2026-11.jsonl').read_bytes() == before
    # Even if the source changed between the runs, the day keeps the rows of its first run.
    register.write_text(REGISTER.replace('Example', 'Changed'), encoding='utf-8')
    assert ledger.record('2026-11-23', folder, register) == 0
    assert (folder / '2026-11.jsonl').read_bytes() == before


def test_a_new_day_appends_and_a_new_month_starts_a_new_file(tmp_path, monkeypatch):
    register, folder = setup(tmp_path, monkeypatch)
    ledger.record('2026-11-23', folder, register)
    before = (folder / '2026-11.jsonl').read_bytes()
    ledger.record('2026-11-24', folder, register)
    after = (folder / '2026-11.jsonl').read_bytes()
    assert after.startswith(before) and len(read(folder, '2026-11.jsonl')) == 4
    ledger.record('2026-12-01', folder, register)
    assert sorted(p.name for p in folder.iterdir()) == ['2026-11.jsonl', '2026-12.jsonl']
