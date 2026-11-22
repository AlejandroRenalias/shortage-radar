import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from triage import counts, level, medicine_name, newly_critical, on_market


def test_levels_for_group_with_others_with_none_without_group_and_veterinary():
    assert level({'atc': 'N05AH04', 'substitution_group': '1299', 'other_packages_count': 5}) == 'substitute'
    assert level({'atc': 'N05AH04', 'substitution_group': '1299', 'other_packages_count': 0}) == 'critical'
    assert level({'atc': 'N05AH04', 'substitution_group': '1299'}) == 'critical'
    assert level({'atc': 'L01AA01', 'substitution_group': '', 'other_packages_count': 0}) == 'nogroup'
    assert level({'atc': 'L01AA01'}) == 'nogroup'
    # Veterinary medicines are counted apart, even with a group or other packages.
    assert level({'atc': 'QJ01CA04', 'substitution_group': '', 'other_packages_count': 0}) == 'vet'
    assert level({'atc': 'QJ01CA04', 'substitution_group': '7', 'other_packages_count': 3}) == 'vet'
    assert counts([{'impact': 'critical'}, {'atc': 'QA'}, {'substitution_group': '1', 'other_packages_count': 2}]) == {'substitute': 1, 'critical': 1, 'nogroup': 0, 'vet': 1}


def test_medicine_names_drop_salts_but_keep_salts_that_are_the_substance():
    assert medicine_name('Quetiapine fumarate') == 'Quetiapine'
    assert medicine_name('Ipratropium bromide monohydrate') == 'Ipratropium'
    assert medicine_name('Paracetamol, Codeine phosphate hemihydrate') == 'Paracetamol + Codeine'
    assert medicine_name('Calcium folinate') == 'Calcium folinate'
    assert medicine_name('Sodium sulphate anhydrous') == 'Sodium sulphate anhydrous'
    assert medicine_name('Octreotide acetate, Octreotide acetate') == 'Octreotide'
    # A mixture of many substances is named by its product instead.
    assert medicine_name('Macrogol 3350, Sodium chloride, Potassium chloride') == ''
    assert medicine_name('') == ''


def test_market_dates():
    assert on_market({'market': '1', 'entry': '2020-01-01', 'exit': None}, '2026-11-01')
    assert not on_market({'market': '1', 'entry': '2026-11-10', 'exit': None}, '2026-11-01')
    assert not on_market({'market': '0', 'entry': '2020-01-01', 'exit': '2026-10-01'}, '2026-11-01')
    assert on_market({'market': '0', 'entry': '2020-01-01', 'exit': '2026-12-01'}, '2026-11-01')
    assert on_market({'market': '1', 'entry': '2026-06-01', 'exit': '2025-01-01'}, '2026-11-01')  # back on the market after an earlier exit
    assert not on_market({'market': '0', 'entry': None, 'exit': None}, '2026-11-01')


def pack(vnr, entry='2020-01-01', exit_=None, old=()):
    return {'vnr': vnr, 'old': set(old), 'market': '1', 'entry': entry, 'exit': exit_}


def captures(days, listed):
    return [(d, [{'NordicArticleNumber': v} for v in vs]) for d, vs in zip(days, listed)]


DAYS = ['2026-11-01', '2026-11-02', '2026-11-03', '2026-11-04', '2026-11-05', '2026-11-06']


def test_newly_critical_needs_two_captures_in_a_row():
    members = {'42': [pack('000001'), pack('000002')]}
    # 000001 is short from the start; its only alternative goes short on 3 Nov and stays short.
    events = newly_critical(captures(DAYS, [['000001'], ['000001'], ['000001', '000002'], ['000001', '000002'], ['000001', '000002'], ['000001']]), members)
    assert events == [{'group': '42', 'date': '2026-11-03', 'after': '2026-11-02', 'vnrs': ['000001', '000002']}]
    # A one-capture glitch is not an event.
    assert newly_critical(captures(DAYS, [['000001'], ['000001'], ['000001', '000002'], ['000001'], ['000001'], ['000001']]), members) == []
    # A change in the latest capture waits for the next one.
    assert newly_critical(captures(DAYS, [['000001']] * 5 + [['000001', '000002']]), members) == []


def test_a_one_capture_recovery_does_not_make_a_second_event():
    members = {'42': [pack('000001'), pack('000002')]}
    both, one = ['000001', '000002'], ['000001']
    events = newly_critical(captures(DAYS, [one, one, both, both, one, both]), members)
    assert [e['date'] for e in events] == ['2026-11-03']
    # A recovery that holds two captures, then a new loss, is a second event.
    seven = DAYS + ['2026-11-07', '2026-11-08']
    events = newly_critical(captures(seven, [one, both, both, one, one, both, both, both]), members)
    assert [e['date'] for e in events] == ['2026-11-02', '2026-11-06']


def test_single_package_group_counts_when_it_goes_short_and_old_numbers_match():
    members = {'7': [pack('100001', old={'555555'})]}
    events = newly_critical(captures(DAYS[:4], [[], [], ['555555'], ['555555']]), members)
    assert events == [{'group': '7', 'date': '2026-11-03', 'after': '2026-11-02', 'vnrs': ['555555']}]


def test_alternative_leaving_the_market_and_one_not_yet_launched():
    left = {'42': [pack('000001'), pack('000002', exit_='2026-11-03')]}
    events = newly_critical(captures(DAYS[:4], [['000001']] * 4), left)
    assert [e['date'] for e in events] == ['2026-11-03']
    # A package launched later was not an alternative before its launch, so the group was already critical: no event.
    launched = {'42': [pack('000001'), pack('000002', entry='2026-11-04')]}
    assert newly_critical(captures(DAYS[:4], [['000001']] * 4), launched) == []


def test_a_long_gap_resets_the_state_so_no_event_is_dated_across_it():
    members = {'42': [pack('000001'), pack('000002')]}
    days = ['2024-11-18', '2026-09-15', '2026-09-23', '2026-10-06']
    assert newly_critical(captures(days, [['000001'], ['000001', '000002'], ['000001', '000002'], ['000001', '000002']]), members) == []
    # Confirmation across a long gap does not count either.
    days = ['2026-09-01', '2026-09-02', '2026-09-03', '2026-10-30']
    assert newly_critical(captures(days, [['000001'], ['000001'], ['000001', '000002'], ['000001', '000002']]), members) == []


def test_record_keeps_one_entry_per_snapshot_date(tmp_path, monkeypatch):
    import record_triage
    monkeypatch.setattr(record_triage, 'load_snapshots', lambda: ([('2026-11-21', [{'NordicArticleNumber': '000001'}]), ('2026-11-22', [{'NordicArticleNumber': '000001'}, {'NordicArticleNumber': '000002'}])], set()))
    monkeypatch.setattr(record_triage, 'register', lambda path, wanted, current: {'000001': {'substitution_group': '4', 'other_packages_count': 0, 'atc': 'N01'}, '000002': {'atc': 'QA01'}})
    monkeypatch.setattr(record_triage, 'register_date', lambda path: '2026-11-22')
    target = tmp_path / 'counts.json'
    target.write_text(json.dumps({'counts': [{'date': '2026-11-21', 'total': 1}, {'date': '2026-11-22', 'total': 9}]}), encoding='utf-8')
    record_triage.record(target, tmp_path / 'register.xml')
    data = json.loads(target.read_text(encoding='utf-8'))
    assert [c['date'] for c in data['counts']] == ['2026-11-21', '2026-11-22']
    assert data['counts'][1] == {'date': '2026-11-22', 'register_date': '2026-11-22', 'total': 2, 'substitute': 0, 'critical': 1, 'nogroup': 0, 'vet': 1}
    assert data['note']
