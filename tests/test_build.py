import sys
from datetime import date, timedelta
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import HEADER, end_date_changes, events, read_snapshot, register


def row(end='2026-12-01', vnr='012345'):
    return dict(zip(HEADER, [vnr, 'K', '2026-11-01', end, '2026-10-01', '2026-11-01', 'Company']))


def test_changes_removal_and_reappearance():
    result, history = events([('2026-11-01', [row()]), ('2026-11-02', [row('2026-12-05')]), ('2026-11-03', []), ('2026-11-04', [row()])])
    assert len(result) == 2
    assert result[0]['first_estimated_end'] == '2026-12-01'
    assert result[0]['end_changes'][-1] == {'seen': '2026-11-02', 'date': '2026-12-05'}
    assert result[0]['last_seen'] == '2026-11-02'
    assert result[0]['removed_on'] == '2026-11-03'
    assert result[1]['removed_on'] is None
    assert history[-1]['count'] == 1


def test_duplicate_identity_rejected():
    with pytest.raises(ValueError, match='duplicate'):
        events([('2026-11-01', [row(), row()])])


def test_bad_file_rejected(tmp_path):
    p = tmp_path / 'bad.txt'
    p.write_text('error page\n', encoding='utf-8')
    with pytest.raises(ValueError, match='header'):
        read_snapshot(p)


def test_register_groups_follow_product_references(tmp_path):
    path = tmp_path / 'register.xml'
    path.write_text('''<Perusrekisteri>
      <Pakkaus Laakevalmiste-ref="p1"><VNR-numero>012345</VNR-numero></Pakkaus>
      <Pakkaus Laakevalmiste-ref="p1"><VNR-numero>012346</VNR-numero></Pakkaus>
      <Pakkaus Laakevalmiste-ref="p2"><VNR-numero>012347</VNR-numero></Pakkaus>
      <Laakevalmiste id="p1"><Kauppanimi>Example</Kauppanimi>
        <Substituutioryhma listname="Substitution Group" id="0042" value="0042"/>
      </Laakevalmiste>
      <Laakevalmiste id="p2"><Substituutioryhma/></Laakevalmiste>
    </Perusrekisteri>''', encoding='utf-8')
    products = register(path, {'012345', '012346', '012347', '999999'})
    assert products['012345']['substitution_group'] == '0042'
    assert products['012346']['substitution_group'] == '0042'
    assert products['012347']['substitution_group'] == ''
    assert '999999' not in products



def test_first_capture_is_marked_and_windows_are_kept():
    result, history = events([('2024-11-18', [row()]), ('2026-09-15', [row(vnr='222222')]), ('2026-09-20', [])])
    first, second = result
    assert first['listed_at_first_capture'] and first['first_seen_after'] is None
    assert first['last_seen'] == '2024-11-18' and first['removed_on'] == '2026-09-15'
    assert not second['listed_at_first_capture'] and second['first_seen_after'] == '2024-11-18'
    assert second['removed_on'] == '2026-09-20'
    assert [h['gap_days'] for h in history] == [None, 666, 5]


def test_package_still_listed_is_flagged_on_removal():
    changed = dict(row(), UnavailableFrom='2026-11-05')
    result, _ = events([('2026-11-01', [row()]), ('2026-11-04', [changed])])
    assert result[0]['removed_on'] == '2026-11-04' and result[0]['vnr_listed_at_removal']


def test_end_date_changes_count_current_notices_changed_between_close_captures():
    def count(shots):
        es, history = events(shots)
        return end_date_changes(es, history)
    shots = [('2026-11-01', [row(vnr='111111'), row(vnr='222222'), row(vnr='333333')]),
             ('2026-11-05', [row('2026-12-09', vnr='111111'), row(vnr='222222'), row('2026-12-09', vnr='333333')]),
             ('2026-11-10', [row('2026-12-20', vnr='111111'), row(vnr='222222')])]
    result = count(shots)
    # 111111 changed twice and counts once; 222222 did not change; 333333 changed but left the list, so it is not current.
    assert result == {'current': 2, 'changed': 1, 'from': '2026-11-01', 'to': '2026-11-10', 'max_gap_days': 14}


def test_end_date_change_across_a_long_gap_is_not_counted():
    # Exactly 14 days is still joined; 15 days is a gap and the change is not counted.
    for days, counted in ((14, 1), (15, 0)):
        later = (date.fromisoformat('2026-11-01') + timedelta(days=days)).isoformat()
        es, history = events([('2026-11-01', [row()]), (later, [row('2026-12-09')])])
        assert end_date_changes(es, history)['changed'] == counted
    # A change after the gap, between two close captures, is counted.
    es, history = events([('2026-09-01', [row()]), ('2026-11-01', [row()]), ('2026-11-03', [row('2026-12-09')])])
    assert end_date_changes(es, history)['changed'] == 1


def test_end_date_changes_with_one_capture():
    es, history = events([('2026-11-01', [row()])])
    assert end_date_changes(es, history) == {'current': 1, 'changed': 0, 'from': '2026-11-01', 'to': '2026-11-01', 'max_gap_days': 14}


def test_imported_dates_yield_to_own_snapshots(tmp_path, monkeypatch):
    import build
    for folder, day in (('', '2026-11-21'), ('imported', '2026-11-21'), ('imported', '2026-11-17')):
        target = tmp_path / 'data/snapshots' / folder
        target.mkdir(parents=True, exist_ok=True)
        (target / f'{day}.txt').write_text(';'.join(f'"{c}"' for c in HEADER) + '\n"012345";"K";"2026-11-01";"2026-12-01";"2026-10-01";"2026-11-01";"' + (folder or 'own') + '"\n', encoding='utf-8')
    monkeypatch.setattr(build, 'ROOT', tmp_path)
    snapshots, imported = build.load_snapshots()
    assert [d for d, _ in snapshots] == ['2026-11-17', '2026-11-21']
    assert snapshots[1][1][0]['Company'] == 'own' and imported == {'2026-11-17'}


def test_old_vnr_keeps_identity_and_maps_current(tmp_path):
    path = tmp_path / 'register.xml'
    path.write_text('<Perusrekisteri><Pakkaus Laakevalmiste-ref="p"><VNR-numero>158928</VNR-numero><VanhaVNR>422093</VanhaVNR></Pakkaus><Laakevalmiste id="p"><Kauppanimi>Example</Kauppanimi></Laakevalmiste></Perusrekisteri>')
    result = register(path, {'422093', '158928'})
    assert result['422093']['name'] == 'Example'
    assert result['422093']['current_vnr'] == '158928'


def test_build_gate_and_csv(tmp_path, monkeypatch):
    import csv
    import json
    import build
    (tmp_path / 'site').mkdir()
    monkeypatch.setattr(build, 'ROOT', tmp_path)
    monkeypatch.setattr(build, 'load_snapshots', lambda: ([('2026-11-01', [row()])], set()))
    monkeypatch.setattr(build, 'read_rss_counts', lambda: [])
    monkeypatch.setattr(build, 'register', lambda *args: {})
    with pytest.raises(ValueError, match='Register matched'):
        build.build()
    assert not (tmp_path / 'site/data.json').exists()
    monkeypatch.setattr(build, 'register', lambda *args: {'012345': {'name': 'Example', 'current_vnr': '222222', 'atc': 'QN01'}})
    monkeypatch.setenv('LAST_CHECKED', '2026-11-02')
    build.build()
    data = json.loads((tmp_path / 'site/data.json').read_text(encoding='utf-8'))
    assert data['last_checked'] == '2026-11-02' and data['generated_at'].endswith('+00:00')
    current = json.loads((tmp_path / 'site/current.json').read_text(encoding='utf-8'))
    history = json.loads((tmp_path / 'site/history.json').read_text(encoding='utf-8'))
    assert len(current['events']) == 1 and 'history' not in current
    source = json.loads((tmp_path / 'site/source.json').read_text(encoding='utf-8'))      # for the EU list pages, which load no other data
    assert source['last_checked'] == '2026-11-02' and set(source) == {'archive_start', 'snapshot_date', 'source_metadata', 'generated_at', 'last_checked'}
    assert history['first_capture_count'] == 1 and 'events' not in history
    assert len(data['events']) == 1 and data['history'] == history['history']
    raw = (tmp_path / 'site/shortages.csv').read_bytes()
    assert raw.startswith(b'\xef\xbb\xbf')
    records = list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
    assert list(records[0]) == ['VNR', 'current VNR', 'name', 'strength', 'form', 'pack', 'active substances', 'ATC', 'company', 'start date', 'estimated end date', 'notification date', 'veterinary', 'other packages on market', 'substitution group', 'impact', 'source credit']
    # The credit goes with every copy of the data: Fimea, the licence and the note that the data was changed.
    assert 'CC BY 4.0' in records[0]['source credit'] and 'Fimea' in records[0]['source credit'] and 'changed the data' in records[0]['source credit']
    for name in ('data.json', 'current.json', 'source.json'):
        assert 'CC BY 4.0' in json.loads((tmp_path / 'site' / name).read_text(encoding='utf-8'))['source_metadata']['source_credit'], name
    assert records[0]['current VNR'] == '222222' and records[0]['veterinary'] == 'yes'
    assert records[0]['other packages on market'] == '' and records[0]['impact'] == 'vet'
    monkeypatch.setattr(build, 'register', lambda *args: {'012345': {'name': 'Example', 'substitution_group': '42', 'other_packages_count': 0}})
    build.build()
    records = list(csv.DictReader((tmp_path / 'site/shortages.csv').read_text(encoding='utf-8-sig').splitlines()))
    assert records[0]['other packages on market'] == '0' and records[0]['substitution group'] == '42' and records[0]['impact'] == 'no_alternative'
    current = json.loads((tmp_path / 'site/current.json').read_text(encoding='utf-8'))
    summary = json.loads((tmp_path / 'site/summary.json').read_text(encoding='utf-8'))
    assert current['events'][0]['impact'] == 'no_alternative'
    assert summary['impact'] == {'substitute': 0, 'no_alternative': 1, 'nogroup': 0, 'vet': 0, 'critical': 1}  # `critical` is the old name, kept for one release


@pytest.mark.parametrize('reverse', [False, True])
def test_exact_vnr_takes_priority_over_old_vnr(tmp_path, reverse):
    path = tmp_path / 'register.xml'
    packages = [
        '<Pakkaus Laakevalmiste-ref="a"><VNR-numero>196862</VNR-numero><VanhaVNR>551292</VanhaVNR></Pakkaus>',
        '<Pakkaus Laakevalmiste-ref="b"><VNR-numero>551292</VNR-numero><VanhaVNR>196862</VanhaVNR></Pakkaus>',
    ]
    if reverse: packages.reverse()
    path.write_text('<Perusrekisteri>' + ''.join(packages) + '<Laakevalmiste id="a"><Kauppanimi>First</Kauppanimi></Laakevalmiste><Laakevalmiste id="b"><Kauppanimi>Second</Kauppanimi></Laakevalmiste></Perusrekisteri>')
    products = register(path, {'196862', '551292'})
    assert (products['196862']['name'], products['196862']['current_vnr']) == ('First', '196862')
    assert (products['551292']['name'], products['551292']['current_vnr']) == ('Second', '551292')


@pytest.mark.parametrize('reverse', [False, True])
def test_old_vnr_prefers_nonempty_current_number(tmp_path, reverse):
    path = tmp_path / 'register.xml'
    packages = [
        '<Pakkaus Laakevalmiste-ref="empty"><VanhaVNR>550343</VanhaVNR></Pakkaus>',
        '<Pakkaus Laakevalmiste-ref="filled"><VNR-numero>123456</VNR-numero><VanhaVNR>550343</VanhaVNR></Pakkaus>',
    ]
    if reverse: packages.reverse()
    path.write_text('<Perusrekisteri>' + ''.join(packages) + '<Laakevalmiste id="empty"><Kauppanimi>Empty</Kauppanimi></Laakevalmiste><Laakevalmiste id="filled"><Kauppanimi>Filled</Kauppanimi></Laakevalmiste></Perusrekisteri>')
    product = register(path, {'550343'})['550343']
    assert (product['name'], product['current_vnr']) == ('Filled', '123456')


def test_available_packages_exclude_shortages_and_old_vnrs(tmp_path):
    path = tmp_path / 'register.xml'
    def pack(vnr, ref, market='1', short='0', old=''):
        return f'<Pakkaus Laakevalmiste-ref="{ref}"><VNR-numero>{vnr}</VNR-numero><VanhaVNR>{old}</VanhaVNR><Kaupanolo><Kaupan>{market}</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>{short}</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>'
    packages = [pack('000001','none'), pack('000002','short'), pack('000003','short',short='1'),
                pack('000004','available'), pack('000005','available'), pack('000006','available',market='0'),
                pack('000007','available',short='1'), pack('000008','available',old='999999'),
                pack('000009','available',short=''), pack('000010','available')]
    products = '<Laakevalmiste id="none"/><Laakevalmiste id="short"><Vahvuus>10 mg</Vahvuus><Laakemuoto value="tabletti"/><Substituutioryhma value="s"/></Laakevalmiste><Laakevalmiste id="available"><Vahvuus>10 mg</Vahvuus><Laakemuoto value="tabletti"/><Substituutioryhma value="a"/></Laakevalmiste>'
    path.write_text('<Perusrekisteri>' + ''.join(packages) + products + '</Perusrekisteri>', encoding='utf-8')
    result = register(path, {'000001','000002','000004'}, {'000001','000002','000004','999999','000010'})
    assert result['000001']['substitution_group'] == '' and result['000001']['other_packages_count'] == 0
    assert result['000002']['other_packages_count'] == 0
    assert result['000004']['other_packages_count'] == 1


def test_substitution_group_code_decides_not_strength_or_form_text(tmp_path):
    """The register writes one group's strength and form in different ways ("20 mg/ml" and "20 mg/g", film-coated
    tablets and capsules). Fimea's group code is the decision on interchangeability, so only the code is compared."""
    path = tmp_path / 'register.xml'
    def product(id, strength, form, group='42'):
        return f'<Laakevalmiste id="{id}"><Substituutioryhma value="{group}"/><Vahvuus>{strength}</Vahvuus><Laakemuoto value="{form}"/></Laakevalmiste>'
    def pack(vnr, ref):
        return f'<Pakkaus Laakevalmiste-ref="{ref}"><VNR-numero>{vnr}</VNR-numero><Kaupanolo><Kaupan>1</Kaupan></Kaupanolo><SaatavuushairioTiedot><Saatavuushairio>0</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>'
    specs = [('a', '20 mg', 'tabletti, kalvopäällysteinen'), ('b', '20 mg', 'kapseli, kova'), ('c', '', 'tabletti'), ('d', '20 mg', 'tabletti', '43'), ('e', '20 mg', 'tabletti', '')]
    path.write_text('<Perusrekisteri>' + ''.join(pack(f'{i:06}', x[0]) for i, x in enumerate(specs, 1)) + ''.join(product(*x) for x in specs) + '</Perusrekisteri>', encoding='utf-8')
    members = {}
    found = register(path, {'000001', '000003', '000004', '000005'}, {'000001'}, members)
    assert found['000001']['other_packages_count'] == 2  # 000002 and 000003, whatever their strength and form text
    assert found['000003']['other_packages_count'] == 1  # 000002; 000001 is in the shortage file
    assert found['000004']['other_packages_count'] == 0  # alone in group 43
    assert found['000005']['substitution_group'] == '' and found['000005']['other_packages_count'] == 0
    assert sorted(members) == ['42', '43'] and [p['vnr'] for p in members['42']] == ['000001', '000002', '000003']
    assert 'holder' not in found['000001']


def test_current_view_and_history_use_one_definition_of_an_available_alternative(tmp_path):
    """F14: the impact level (register()), the medicine page list (group_lists) and the latest capture of the history
    (group_states) all call triage.is_available_alternative, so they cannot disagree on the same register. Every combination of
    the fields the rule reads is tried against one listed package."""
    import itertools
    from build import group_lists, helsinki_today
    from triage import group_states
    day = '2026-11-23'
    cases = list(itertools.product(['1', '0'], ['0', '1', ''], ['', '2020-01-01', '2026-12-01'], ['', '2026-01-01', '2030-01-01']))
    packages, products = [], ''
    for n, (market, short, entry, exit_) in enumerate(cases):
        group = f'g{n}'
        for vnr, listed_one in ((f'1{n:05}', True), (f'2{n:05}', False)):
            kaupanolo = f'<Kaupanolo><Kaupan>{market if not listed_one else 1}</Kaupan>' + (f'<Kauppaantulopaiva>{entry}</Kauppaantulopaiva>' if entry and not listed_one else '') + (f'<Kaupastapoistumispaiva>{exit_}</Kaupastapoistumispaiva>' if exit_ and not listed_one else '') + '</Kaupanolo>'
            flag = f'<SaatavuushairioTiedot><Saatavuushairio>{short if not listed_one else 1}</Saatavuushairio></SaatavuushairioTiedot>'
            packages.append(f'<Pakkaus Laakevalmiste-ref="{group}"><VNR-numero>{vnr}</VNR-numero>{kaupanolo}{flag}</Pakkaus>')
        products += f'<Laakevalmiste id="{group}"><Vahvuus>1 mg</Vahvuus><Laakemuoto value="tabletti"/><Substituutioryhma value="{group}"/></Laakevalmiste>'
    path = tmp_path / 'register.xml'
    path.write_text('<Perusrekisteri>' + ''.join(packages) + products + '</Perusrekisteri>', encoding='utf-8')
    listed = {f'1{n:05}' for n in range(len(cases))}
    members = {}
    found = register(path, listed, listed, members, day=day)
    alias = {p['vnr']: g for g, ps in members.items() for p in ps}
    states = group_states(day, [{'NordicArticleNumber': v} for v in sorted(listed)], members, alias, True)
    current = [{'substitution_group': found[v]['substitution_group']} for v in sorted(listed)]
    lists = group_lists(current, members, listed, day)
    for n, (market, short, entry, exit_) in enumerate(cases):
        group = f'g{n}'
        count = found[f'1{n:05}']['other_packages_count']
        assert (count > 0) == (not states[group]) == bool(lists[group]['available']), (market, short, entry, exit_)
    # Reading the cases: the flag must say on the market and not short, and the dates must not contradict it.
    by_case = {c: found[f'1{n:05}']['other_packages_count'] for n, c in enumerate(cases)}
    assert by_case[('1', '0', '', '')] == 1
    assert by_case[('1', '0', '2020-01-01', '')] == 1
    assert by_case[('0', '0', '2020-01-01', '')] == 0     # the nine packages of 23 Nov 2026: dates say yes, the register flag says no
    assert by_case[('1', '1', '', '')] == 0 and by_case[('1', '', '', '')] == 0
    assert by_case[('1', '0', '2026-12-01', '')] == 0 and by_case[('1', '0', '2020-01-01', '2026-01-01')] == 0
    assert by_case[('1', '0', '2020-01-01', '2030-01-01')] == 1
    assert helsinki_today() >= '2026-11-23'
