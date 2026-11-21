import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import HEADER, delay_stats, events, read_snapshot, register


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


def test_delay_stats_bounds_and_exclusions():
    def ev(vnr, first_after, first, last, removed, end, **extra):
        return dict(dict(NordicArticleNumber=vnr, first_seen_after=first_after, first_seen=first, last_seen=last, removed_on=removed, first_estimated_end=end, listed_at_first_capture=False), **extra)
    all_events = [
        ev('1', '2026-10-01', '2026-10-03', '2026-10-20', '2026-10-24', '2026-10-10'),   # past the estimate
        ev('2', '2026-10-01', '2026-10-03', '2026-10-05', '2026-10-08', '2026-10-10'),   # gone by it
        ev('3', '2026-10-01', '2026-10-03', '2026-10-08', '2026-10-12', '2026-10-10'),   # cannot be told
        ev('4', None, '2026-10-03', '2026-10-05', '2026-10-08', '2026-10-10', listed_at_first_capture=True),
        ev('5', '2024-11-18', '2026-09-15', '2026-10-05', '2026-10-08', '2026-10-10'),   # first seen after a long gap
        ev('6', '2026-10-01', '2026-10-03', '2026-10-05', '2026-10-08', '2026-10-10', vnr_listed_at_removal=True),
        ev('7', '2026-10-01', '2026-10-03', '2026-10-05', None, '2026-10-10'),            # still listed
    ]
    stats = delay_stats(all_events)
    assert (stats['sample_size'], stats['past_estimate'], stats['not_past_estimate'], stats['undetermined']) == (3, 1, 1, 1)
    assert stats['excluded'] == {'listed_at_first_capture': 1, 'no_estimate': 0, 'wide_start_window': 1, 'wide_removal_window': 0, 'vnr_still_listed': 1}
    assert (stats['median_overrun_min_days'], stats['median_overrun_max_days']) == (10, 14)
    assert not stats['meaningful'] and 'share_past_min' not in stats


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


def test_active_past_estimate_requires_known_narrow_first_window():
    def active(first_after, first, estimate, last='2026-11-21', first_capture=False):
        return dict(removed_on=None, first_seen_after=first_after, first_seen=first,
                    first_estimated_end=estimate, last_seen=last, listed_at_first_capture=first_capture)
    stats = delay_stats([
        active('2026-10-01', '2026-10-15', '2026-11-20'),
        active('2026-10-01', '2026-10-16', '2026-11-01'),
        active(None, '2026-10-01', '2026-11-01', first_capture=True),
        active('2026-10-01', '2026-10-15', '2026-11-21'),
        active('2026-10-01', '2026-10-15', ''),
    ])
    assert stats['active_past_estimate'] == 1
    assert stats['sample_size'] == 0


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
    assert history['first_capture_count'] == 1 and 'events' not in history
    assert len(data['events']) == 1 and data['history'] == history['history']
    raw = (tmp_path / 'site/shortages.csv').read_bytes()
    assert raw.startswith(b'\xef\xbb\xbf')
    records = list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
    assert list(records[0]) == ['VNR', 'current VNR', 'name', 'strength', 'form', 'pack', 'active substances', 'ATC', 'company', 'start date', 'estimated end date', 'notification date', 'veterinary', 'other packages on market']
    assert records[0]['current VNR'] == '222222' and records[0]['veterinary'] == 'yes'


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
    products = '<Laakevalmiste id="none"/><Laakevalmiste id="short"><Substituutioryhma value="s"/></Laakevalmiste><Laakevalmiste id="available"><Substituutioryhma value="a"/></Laakevalmiste>'
    path.write_text('<Perusrekisteri>' + ''.join(packages) + products + '</Perusrekisteri>', encoding='utf-8')
    result = register(path, {'000001','000002','000004'}, {'000001','000002','000004','999999','000010'})
    assert result['000001']['substitution_group'] == '' and result['000001']['other_packages_count'] == 0
    assert result['000002']['other_packages_count'] == 0
    assert result['000004']['other_packages_count'] == 1
