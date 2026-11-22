import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from slices import LONGEST, NEWEST, package_shards, shard_name, summary

META = {'archive_start': '2024-11-18', 'snapshot_date': '2026-11-22', 'source_metadata': {}, 'generated_at': 'x', 'last_checked': None}


def event(vnr, start, company='Orion', form='tabletti', atc='N02AA', removed=None):
    return {'NordicArticleNumber': vnr, 'UnavailableFrom': start, 'Company': company, 'form': form, 'atc': atc, 'removed_on': removed}


def test_every_shard_exists_and_packages_land_by_last_two_digits():
    events = [event('599361', '2026-11-01'), event('123461', '2026-10-01', removed='2026-11-10'), event('555555', '2026-11-05')]
    shards = package_shards(events, META)
    assert sorted(shards) == [f'{n:02d}' for n in range(100)]
    assert shard_name('599361') == '61'
    assert [e['NordicArticleNumber'] for e in shards['61']['events']] == ['599361', '123461']
    assert shards['55']['events'][0]['NordicArticleNumber'] == '555555'
    assert shards['00']['events'] == [] and shards['00']['snapshot_date'] == '2026-11-22'


def test_summary_counts_and_picks_the_oldest_and_newest_started_packages():
    current = [event(f'{i:06d}', f'2026-11-{i:02d}', company='A' if i % 2 else 'B', form='kapseli' if i < 6 else 'tabletti', atc='S01XA' if i < 4 else 'N02AA') for i in range(1, 21)]
    current.append(event('999999', '2027-01-01'))
    s = summary(current, META)
    assert s['total'] == 21 and s['company_count'] == 3
    assert s['forms'] == {'kapseli': 5, 'tabletti': 16}
    assert s['atc']['S01'] == 3 and s['atc']['N02'] == 18
    assert len(s['longest']) == LONGEST and s['longest'][0]['UnavailableFrom'] == '2026-11-01'
    assert len(s['newest']) == NEWEST and s['newest'][0]['UnavailableFrom'] == '2026-11-20'
    assert all(e['UnavailableFrom'] <= META['snapshot_date'] for e in s['newest'] + s['longest'])
