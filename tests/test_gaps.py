import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build
import critical
import gaps
import triage
from build import HEADER, events
from changes import feeds

ROOT = Path(__file__).resolve().parents[1]


def row(vnr='111111', ending='2027-01-01'):
    return dict(zip(HEADER, [vnr, 'K', '2026-01-01', ending, '2026-01-01', '2026-01-01', 'Company']))


def after(day, n):
    return (date.fromisoformat(day) + timedelta(days=n)).isoformat()


def test_one_threshold_for_the_whole_build():
    assert gaps.MAX_GAP_DAYS == 14
    assert build.MAX_GAP_DAYS is gaps.MAX_GAP_DAYS and critical.MAX_GAP_DAYS is gaps.MAX_GAP_DAYS
    assert not hasattr(triage, 'MAX_GAP_DAYS')
    assert (gaps.is_gap('2026-01-01', '2026-01-15'), gaps.is_gap('2026-01-01', '2026-01-16')) == (False, True)


def test_exactly_14_days_is_joined_and_15_days_is_a_gap():
    start = '2026-03-01'
    for days, spans, gap in ((14, 1, None), (15, 2, 15)):
        second = after(start, days)
        es, history = events([(start, [row()]), (second, [row()])])
        e = es[0]
        assert len(es) == 1 and e['removed_on'] is None
        assert (e['first_seen'], e['last_seen']) == (start, second)
        assert len(e['spans']) == spans
        if gap:
            assert e['spans'] == [{'first_seen': start, 'last_seen': start}, {'first_seen': second, 'last_seen': second}]
            assert e['gaps'] == [{'from': start, 'to': second, 'days': 15}]
        else:
            assert e['spans'] == [{'first_seen': start, 'last_seen': second}] and e['gaps'] == []


def test_spans_continue_after_a_short_step_and_split_at_each_long_gap():
    days = ['2026-01-01', '2026-01-08', '2026-02-01', '2026-02-05', '2026-03-10']
    es, _ = events([(d, [row()]) for d in days])
    assert es[0]['spans'] == [{'first_seen': '2026-01-01', 'last_seen': '2026-01-08'}, {'first_seen': '2026-02-01', 'last_seen': '2026-02-05'}, {'first_seen': '2026-03-10', 'last_seen': '2026-03-10'}]
    assert [g['days'] for g in es[0]['gaps']] == [24, 33]


def test_removal_after_a_long_gap_is_marked_unknown():
    es, _ = events([('2026-01-01', [row()]), ('2026-01-15', [row()]), ('2026-01-30', [row('222222')]), ('2026-02-10', [row('222222')])])
    gone = next(e for e in es if e['NordicArticleNumber'] == '111111')
    assert (gone['removed_on'], gone['removed_after_gap']) == ('2026-01-30', True)  # 15 days after the last capture that listed it
    es, _ = events([('2026-01-01', [row()]), ('2026-01-15', [row()]), ('2026-01-29', [row('222222')])])
    assert es[0]['removed_after_gap'] is False  # exactly 14 days


def test_package_114636_is_not_shown_as_listed_between_its_captures():
    snapshots, _ = build.load_snapshots()
    es, history = events(snapshots)
    current = [e for e in es if e['NordicArticleNumber'] == '114636' and e['removed_on'] is None]
    assert len(current) == 1
    e = current[0]
    assert (e['first_seen'], e['last_seen']) == ('2024-11-18', max(d for d, _ in snapshots))
    assert e['spans'][0] == {'first_seen': '2024-11-18', 'last_seen': '2024-11-18'}
    assert e['spans'][1]['first_seen'] == '2026-09-15'
    assert e['gaps'] == [{'from': '2024-11-18', 'to': '2026-09-15', 'days': 666}]
    # No gap above the limit hides inside a span.
    days = [d for d, _ in snapshots]
    for ev in es:
        for s in ev['spans']:
            inside = [d for d in days if s['first_seen'] <= d <= s['last_seen']]
            assert all(not gaps.is_gap(a, b) for a, b in zip(inside, inside[1:]))


def test_feed_entry_names_the_unobserved_stretch():
    snapshots = [('2026-10-01', [row()]), ('2026-11-01', [row()]), ('2026-11-10', [row('333333')])]
    es, history = events(snapshots)
    es[0]['name'] = 'Medicine'
    en = feeds(es, snapshots, history)
    assert 'Not observed between 1 Oct 2026 and 1 Nov 2026.' in en['feed.xml']
    assert 'Ei havaintoja välillä 1.10.2026–1.11.2026.' in en['feed-fi.xml']


def test_the_threshold_is_stated_on_the_methods_page():
    from critical_pages import render_critical
    eu = critical.load_eu_list()
    page = render_critical({'eu': eu, 'rows': [], 'counts': critical.counts([]), 'history': {}, 'archive_start': '2026-09-15', 'snapshot_date': '2026-11-23', 'source_metadata': {}})['critical-methods.html']
    assert f'more than {gaps.MAX_GAP_DAYS} days apart' in page and 'Gaps in the captures' in page
