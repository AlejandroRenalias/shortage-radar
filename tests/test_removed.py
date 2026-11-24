import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from removed import FIELDS, removed_index


def event(vnr, first, last, removed, name='Elvanse', **extra):
    return dict({'NordicArticleNumber': vnr, 'first_seen': first, 'last_seen': last, 'removed_on': removed, 'name': name, 'Company': 'Takeda', 'gaps': [], 'removed_after_gap': False,
                 'UnavailableFrom': '2026-01-01', 'EndingDate': '2027-01-01', 'impact': 'no_alternative'}, **extra)


def test_only_packages_that_are_not_listed_now_are_in_the_index():
    events = [event('111111', '2026-09-01', '2026-09-15', '2026-09-23'), event('222222', '2026-09-01', '2026-09-15', '2026-09-23'), event('222222', '2026-10-01', '2026-11-20', None)]
    assert [r['NordicArticleNumber'] for r in removed_index(events)] == ['111111']


def test_one_row_for_each_package_the_most_recently_seen_notice_first():
    old, new = event('111111', '2026-01-01', '2026-02-01', '2026-02-08'), event('111111', '2026-09-01', '2026-09-15', '2026-09-23', name='Elvanse')
    other = event('333333', '2026-10-01', '2026-10-20', '2026-10-27', name='Ozempic')
    rows = removed_index([old, new, other])
    assert [(r['NordicArticleNumber'], r['last_seen']) for r in rows] == [('333333', '2026-10-20'), ('111111', '2026-09-15')]


def test_rows_carry_only_what_the_captures_and_the_register_say_and_keep_the_gaps():
    gaps = [{'from': '2026-01-05', 'to': '2026-03-01', 'days': 55}]
    row, = removed_index([event('111111', '2026-01-01', '2026-03-05', '2026-03-12', gaps=gaps, removed_after_gap=False, strength='')])
    assert set(row) <= set(FIELDS)
    assert row['gaps'] == gaps and row['last_seen'] == '2026-03-05' and row['removed_on'] == '2026-03-12'
    # No impact label, dates of the estimate or flags: a past listing makes no claim about supply.
    assert not {'impact', 'EndingDate', 'UnavailableFrom'} & set(row)
    assert 'strength' not in row and json.dumps(row)


def test_a_removal_after_a_long_gap_is_marked_so_its_date_is_not_shown_as_exact():
    row, = removed_index([event('111111', '2024-11-18', '2024-11-18', '2026-09-15', removed_after_gap=True)])
    assert row['removed_after_gap'] is True
