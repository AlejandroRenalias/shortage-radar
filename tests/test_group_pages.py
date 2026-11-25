"""Group pages (scripts/group_pages.py): the page data must come from the same classification as `alternatives` and `impact`."""
import itertools
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import group_lists, register
from group_pages import group_page, group_shards, shard_name

ROOT = Path(__file__).resolve().parents[1]
META = {'archive_start': '2026-11-01', 'snapshot_date': '2026-11-25', 'source_metadata': {}, 'generated_at': 'x', 'last_checked': None}
DAY = '2026-11-25'


def package(vnr, ref, market='1', short='0', entry='', exit_='', old=''):
    kaupan = f'<Kaupanolo><Kaupan>{market}</Kaupan>' + (f'<Kauppaantulopaiva>{entry}</Kauppaantulopaiva>' if entry else '') + (f'<Kaupastapoistumispaiva>{exit_}</Kaupastapoistumispaiva>' if exit_ else '') + '</Kaupanolo>'
    return f'<Pakkaus Laakevalmiste-ref="{ref}"><VNR-numero>{vnr}</VNR-numero>{"<VanhaVNR>" + old + "</VanhaVNR>" if old else ""}{kaupan}<SaatavuushairioTiedot><Saatavuushairio>{short}</Saatavuushairio></SaatavuushairioTiedot></Pakkaus>'


def product(ref, group, name='Nimi', strength='1 mg', company='Firma'):
    grp = f'<Substituutioryhma value="{group}"/>' if group else ''
    return f'<Laakevalmiste id="{ref}"><Kauppanimi>{name}</Kauppanimi><Vahvuus>{strength}</Vahvuus><Laakemuoto value="tabletti"/>{grp}<Myyntilupa><Haltija>{company}</Haltija></Myyntilupa></Laakevalmiste>'


def test_page_alternatives_equal_the_impact_count_for_every_combination_of_register_fields(tmp_path):
    """Every combination of the fields the rule reads, one listed package and one other package in each group: the page's alternatives,
    the `other_packages_count` of the listed package and the medicine page list always agree."""
    cases = list(itertools.product(['1', '0'], ['0', '1', ''], ['', '2020-01-01', '2026-12-01'], ['', '2026-01-01', '2030-01-01']))
    packs, prods = [], []
    for n, (market, short, entry, exit_) in enumerate(cases):
        packs.append(package(f'1{n:05}', f'a{n}'))
        packs.append(package(f'2{n:05}', f'b{n}', market, short, entry, exit_))
        prods += [product(f'a{n}', f'{n:04}', 'Listed'), product(f'b{n}', f'{n:04}', 'Other', company=f'Firma {n % 3}')]
    path = tmp_path / 'register.xml'
    path.write_text('<Perusrekisteri>' + ''.join(packs + prods) + '</Perusrekisteri>', encoding='utf-8')
    listed = {f'1{n:05}' for n in range(len(cases))}
    members = {}
    found = register(path, listed, listed, members, day=DAY)
    codes = {found[v]['substitution_group'] for v in listed}
    shards = group_shards(codes, members, listed, DAY, listed, META)
    lists = group_lists([{'substitution_group': c} for c in codes], members, listed, DAY)
    for n in range(len(cases)):
        page = shards[shard_name(f'{n:04}')]['groups'][f'{n:04}']
        assert page['counts']['alternatives'] == found[f'1{n:05}']['other_packages_count'] == len(lists[f'{n:04}']['available']) == sum(p['alt'] for p in page['packages'])
        assert page['counts']['listed'] == sum(p['listed'] for p in page['packages']) == 1
        assert page['packages'][0]['listed'] is True


def test_listed_by_old_vnr_counts_once_and_a_group_without_a_listed_package_has_no_page(tmp_path):
    packs = [package('100001', 'a', old='100009'), package('100002', 'a'), package('100003', 'a', market='0'),
             package('200001', 'b'), package('200002', 'b'), package('300001', 'c')]
    prods = [product('a', '0001'), product('b', '0002'), product('c', '')]
    path = tmp_path / 'register.xml'
    path.write_text('<Perusrekisteri>' + ''.join(packs + prods) + '</Perusrekisteri>', encoding='utf-8')
    listed = {'100009', '300001'}   # a notice under the old VNR of 100001, and a package without a group
    members = {}
    found = register(path, listed, listed, members, day=DAY)
    assert found['100009']['current_vnr'] == '100001' and found['300001']['substitution_group'] == ''
    shards = group_shards({'0001'}, members, listed, DAY, {'100009'}, META)
    page = shards['01']['groups']['0001']
    assert page['counts'] == {'market': 2, 'listed': 1, 'alternatives': 1, 'companies': 1}   # 100003 is off the market and not listed: no row
    assert [(p['vnr'], p['listed'], p['link']) for p in page['packages']] == [('100001', True, '100009'), ('100002', False, '')]
    assert found['100009']['other_packages_count'] == page['counts']['alternatives']
    # Group 0002 has no listed package, and a package without a group has no page: neither is in any file.
    every = group_shards({'0001', '0002', ''}, members, listed, DAY, set(), META)
    assert [c for s in every.values() for c in s['groups']] == ['0001']
    assert sorted(every) == [f'{n:02d}' for n in range(100)] and every['00']['snapshot_date'] == '2026-11-25'


def test_heading_comes_from_the_listed_packages_and_rows_list_the_listed_first():
    def member(vnr, name, substances, listed):
        return ({'vnr': vnr, 'old': set(), 'market': '1', 'short': False, 'name': name, 'strength': '18 mikrog', 'form': 'inhalaatiojauhe', 'pack': '30', 'pack_label': {'en': '30', 'fi': '30'},
                 'company': 'X', 'substances': substances, 'entry': '', 'exit': ''}, listed, not listed)
    rows = [member('1', 'Tiogiva', 'Tiotropium bromide monohydrate, Lactose anhydrous', False), member('2', 'Tiogiva', 'Tiotropium bromide monohydrate, Lactose anhydrous', False),
            member('3', 'Stada', 'Tiotropium bromide monohydrate', True), member('4', 'Salt', 'Rivastigmine hydrogen tartrate', True)]
    assert group_page(rows[:3], set())['heading']['substance'] == 'Tiotropium'
    assert group_page(rows[3:], set())['heading']['substance'] == 'Rivastigmine'
    assert [p['vnr'] for p in group_page(rows[:3], set())['packages']] == ['3', '1', '2']


@pytest.mark.skipif(not (ROOT / 'site/current.json').exists() or not (ROOT / 'site/g/00.json').exists(), reason='needs a build (python scripts/build.py); the pages-build job runs it')
def test_real_build_every_group_page_agrees_with_current_json():
    """Exhaustive, over the real build output: for every group on the list, the page's alternatives count is the value current.json holds
    for each of its packages, and the rows marked as on the shortage list are exactly the listed packages of the group."""
    current = json.loads((ROOT / 'site/current.json').read_text(encoding='utf-8'))['events']
    pages = {}
    for n in range(100):
        shard = json.loads((ROOT / f'site/g/{n:02d}.json').read_text(encoding='utf-8'))
        for code, page in shard['groups'].items():
            assert shard_name(code) == f'{n:02d}' and code not in pages
            pages[code] = page
    by_group = {}
    for e in current:
        if e.get('substitution_group'):
            by_group.setdefault(e['substitution_group'], []).append(e)
    assert set(pages) == set(by_group) and len(pages) > 300      # a page for every group with a listed package, and for no other
    for code, events in by_group.items():
        page = pages[code]
        assert {e['other_packages_count'] for e in events} == {page['counts']['alternatives']}, code
        assert page['counts']['alternatives'] == sum(p['alt'] for p in page['packages']) and page['counts']['listed'] == sum(p['listed'] for p in page['packages'])
        assert page['counts']['listed'] == len({e.get('current_vnr') or e['NordicArticleNumber'] for e in events}), code
        assert {p['vnr'] for p in page['packages'] if p['listed']} == {e.get('current_vnr') or e['NordicArticleNumber'] for e in events}, code
        assert page['counts']['companies'] == len(page['alt_companies']) <= page['counts']['alternatives']
        assert all(p['listed'] for p in page['packages'][:page['counts']['listed']])         # listed ones first
        assert not any(p['alt'] and p['listed'] for p in page['packages'])
    nogroup = {e['NordicArticleNumber'] for e in current if not e.get('substitution_group')}
    assert not nogroup & {p['vnr'] for g in pages.values() for p in g['packages']}            # a package without a group is on no group page
    sizes = [(ROOT / f'site/g/{n:02d}.json').stat().st_size for n in range(100)]
    assert max(sizes) < 60000, max(sizes)                                                    # small files, one per two last digits
