import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import medicine_pages
from medicine_pages import NOT_FOR_MEDICINE_PAGE, attach, build_pages, page_data, verified_groups
from test_audit_groups import DAY, pkg

BOX = ['5', 'Blister']
META = {'archive_start': '2026-11-21', 'snapshot_date': '2026-11-24', 'source_metadata': {}, 'generated_at': 'x', 'last_checked': None}


def event(vnr, removed=None, **kw):
    return dict({'NordicArticleNumber': vnr, 'name': 'Medicine', 'strength': '20 mg', 'first_seen': '2026-11-21', 'last_seen': '2026-11-24', 'removed_on': removed,
                 'substitution_group': '100', 'other_packages_count': 4, 'impact': 'substitute', 'pack_label': {'en': f'pack {vnr}', 'fi': f'pakkaus {vnr}'}}, **kw)


def test_verified_group_gets_a_page_with_each_package_apart(tmp_path, monkeypatch):
    packages = [pkg('1', product='P', container=BOX), pkg('2', product='P', container=BOX), pkg('3', product='OTHER', strength='40 mg')]
    events = [event('1'), event('1', removed='2026-11-23', first_seen='2026-11-01', last_seen='2026-11-10'), event('2'), event('3')]
    monkeypatch.setattr(medicine_pages, 'read_register', lambda path: packages)
    counts = build_pages('register.xml', DAY, {'1', '2', '3'}, events, META, tmp_path)
    # 3 has another strength: a group of one: it is verified too, and gets its own page.
    assert counts['pages'] == 2 and counts['packages_on_pages'] == 3
    ids = {e['NordicArticleNumber']: e['medicine_page'] for e in events}
    assert ids['1'] == ids['2'] != ids['3']
    data = json.loads((tmp_path / f"{ids['1']}.json").read_text(encoding='utf-8'))
    assert [p['vnr'] for p in data['packages']] == ['1', '2']
    # The current notice comes first, then the ended one; every notice stays in its own package row.
    assert [e.get('removed_on') for e in data['packages'][0]['events']] == [None, '2026-11-23']
    assert data['medicine']['substances'] == ['Substance A'] and data['medicine']['strength'] == '20 mg'
    assert data['medicine']['routes'] == ['Suun kautta'] and data['medicine']['atc'] == 'N01AA01'


def test_page_data_carries_no_substitution_stock_or_group_history(tmp_path, monkeypatch):
    packages = [pkg('1', product='P', container=BOX), pkg('2', product='P', container=BOX)]
    events = [event('1'), event('2')]
    monkeypatch.setattr(medicine_pages, 'read_register', lambda path: packages)
    build_pages('register.xml', DAY, {'1', '2'}, events, META, tmp_path)
    [file] = list(tmp_path.glob('m*.json'))
    text = file.read_text(encoding='utf-8')
    data = json.loads(text)
    assert set(data) == {'archive_start', 'snapshot_date', 'source_metadata', 'generated_at', 'last_checked', 'id', 'medicine', 'packages'}
    for key in NOT_FOR_MEDICINE_PAGE + ('medicine_page',):
        assert f'"{key}"' not in text
    assert not re.search(r'"(available|alternatives|market|stock|group_history)', text)


def test_unsure_groups_get_no_page_and_their_notices_are_left_alone(tmp_path, monkeypatch):
    packages = [
        pkg('10', routes=()),                                   # route_not_stated
        pkg('20', product='A', group=''), pkg('21', product='B', group=''),   # two product records, no register group
        pkg('30', form=('900', 'esitäytetty kynä')),            # device-bearing, no device id
        pkg('40', name='Veterinary', vet=True),
        pkg('50', product='P50', old=('55',)),                                 # sure group; notice 55 is joined by an old VNR only
    ]
    events = [event(v) for v in ('10', '20', '21', '30', '40', '55')]
    before = [dict(e) for e in events]
    monkeypatch.setattr(medicine_pages, 'read_register', lambda path: packages)
    counts = build_pages('register.xml', DAY, {e['NordicArticleNumber'] for e in events}, events, META, tmp_path)
    assert counts['pages'] == 0 and not list(tmp_path.glob('m*.json'))
    assert events == before and not any('medicine_page' in e for e in events)


def test_container_guard_keeps_a_mixed_container_group_on_package_pages(tmp_path, monkeypatch):
    packages = [pkg('1', product='P', container=['14', 'Tube']), pkg('2', product='P', container=['11', 'Pump bottle'])]
    events = [event('1'), event('2')]
    monkeypatch.setattr(medicine_pages, 'read_register', lambda path: packages)
    counts = build_pages('register.xml', DAY, {'1', '2'}, events, META, tmp_path)
    assert counts['pages'] == 0 and not any('medicine_page' in e for e in events)


def test_a_vnr_on_two_register_records_is_not_placed(tmp_path, monkeypatch):
    packages = [pkg('1', product='A'), pkg('1', product='B'), pkg('2', product='A')]
    events = [event('1'), event('2')]
    monkeypatch.setattr(medicine_pages, 'read_register', lambda path: packages)
    build_pages('register.xml', DAY, {'1', '2'}, events, META, tmp_path)
    assert not any(e.get('medicine_page') for e in events if e['NordicArticleNumber'] == '1')


def test_stale_pages_are_removed_when_a_build_makes_fewer(tmp_path, monkeypatch):
    (tmp_path / 'mdeadbeef0000.json').write_text('{}', encoding='utf-8')
    monkeypatch.setattr(medicine_pages, 'read_register', lambda path: [pkg('1', product='P', container=BOX)])
    build_pages('register.xml', DAY, {'1'}, [event('1')], META, tmp_path)
    assert not (tmp_path / 'mdeadbeef0000.json').exists() and len(list(tmp_path.glob('m*.json'))) == 1


def test_removed_index_keeps_the_page_id_for_search():
    from removed import removed_index
    e = event('1', removed='2026-11-23', medicine_page='m0123456789ab', gaps=[], name='X')
    assert removed_index([e])[0]['medicine_page'] == 'm0123456789ab'
