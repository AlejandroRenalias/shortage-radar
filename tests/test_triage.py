import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from triage import counts, with_aliases, is_available_alternative, level, medicine_name, newly_critical, on_market


def test_levels_for_group_with_others_with_none_without_group_and_veterinary():
    assert level({'atc': 'N05AH04', 'substitution_group': '1299', 'other_packages_count': 5}) == 'substitute'
    assert level({'atc': 'N05AH04', 'substitution_group': '1299', 'other_packages_count': 0}) == 'no_alternative'
    assert level({'atc': 'N05AH04', 'substitution_group': '1299'}) == 'no_alternative'
    assert level({'atc': 'L01AA01', 'substitution_group': '', 'other_packages_count': 0}) == 'nogroup'
    assert level({'atc': 'L01AA01'}) == 'nogroup'
    # Veterinary medicines are counted apart, even with a group or other packages.
    assert level({'atc': 'QJ01CA04', 'substitution_group': '', 'other_packages_count': 0}) == 'vet'
    assert level({'atc': 'QJ01CA04', 'substitution_group': '7', 'other_packages_count': 3}) == 'vet'
    assert counts([{'impact': 'no_alternative'}, {'atc': 'QA'}, {'substitution_group': '1', 'other_packages_count': 2}]) == {'substitute': 1, 'no_alternative': 1, 'nogroup': 0, 'vet': 1}
    # The old name is read as the new one, and written next to it only by with_aliases.
    assert counts([{'impact': 'critical'}]) == {'substitute': 0, 'no_alternative': 1, 'nogroup': 0, 'vet': 0}
    assert with_aliases(counts([{'impact': 'critical'}])) == {'substitute': 0, 'no_alternative': 1, 'nogroup': 0, 'vet': 0, 'critical': 1}


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
    target.write_text(json.dumps({'counts': [{'date': '2026-11-21', 'total': 1, 'critical': 5}, {'date': '2026-11-22', 'total': 9}]}), encoding='utf-8')
    record_triage.record(target, tmp_path / 'register.xml')
    data = json.loads(target.read_text(encoding='utf-8'))
    assert [c['date'] for c in data['counts']] == ['2026-11-21', '2026-11-22']
    assert data['counts'][1] == {'date': '2026-11-22', 'register_date': '2026-11-22', 'total': 2, 'substitute': 0, 'no_alternative': 1, 'nogroup': 0, 'vet': 1, 'critical': 1}
    # An entry saved under the old name gets the new key with the same value and keeps the old one.
    assert data['counts'][0] == {'date': '2026-11-21', 'total': 1, 'no_alternative': 5, 'critical': 5}
    assert data['note']


def test_one_definition_of_an_available_alternative():
    p = dict(pack('000002'), short=False, shortage_flag='0')
    assert is_available_alternative(p, {'000001'}, '2026-11-23', True) and is_available_alternative(p, {'000001'}, '2026-11-23')
    # In the shortage file (by VNR or old VNR): not available, in both readings.
    assert not is_available_alternative(p, {'000002'}, '2026-11-23', True)
    assert not is_available_alternative(dict(p, old={'999999'}), {'999999'}, '2026-11-02')
    # The register's own flags count only on the register's day; earlier captures read the dates.
    assert not is_available_alternative(dict(p, shortage_flag='1'), set(), '2026-11-23', True)
    assert is_available_alternative(dict(p, shortage_flag='1'), set(), '2026-11-02')
    assert not is_available_alternative(dict(p, market='0'), set(), '2026-11-23', True)
    assert is_available_alternative(dict(p, market='0'), set(), '2026-11-02')
    assert not is_available_alternative(dict(p, shortage_flag=''), set(), '2026-11-23', True)
    # Dates count in both readings.
    assert not is_available_alternative(dict(p, entry='2026-12-01'), set(), '2026-11-23', True)
    assert not is_available_alternative(dict(p, exit='2026-11-03'), set(), '2026-11-23', True)


def test_register_flags_apply_only_to_the_capture_of_the_registers_date():
    """A listed 17 Nov, A+B 18 Nov, A 19 Nov. B is short in the register of 23 Nov. That flag describes 23 Nov, so it must
    not decide the 19 Nov capture: by the dates B is an alternative on 19 Nov, so the loss on 18 Nov (A and B both listed) is not confirmed."""
    members = {'42': [dict(pack('A'), shortage_flag='0'), dict(pack('B'), shortage_flag='1')]}
    shots = captures(['2026-11-17', '2026-11-18', '2026-11-19'], [['A'], ['A', 'B'], ['A']])
    assert newly_critical(shots, members, '2026-11-23') == []
    assert newly_critical(shots, members) == []
    # The same flag in a register dated 19 Nov does describe the 19 Nov capture: B is short there, so the loss holds in two captures.
    assert [e['date'] for e in newly_critical(shots, members, '2026-11-19')] == ['2026-11-18']


def test_the_flag_is_read_only_in_the_capture_dated_like_the_register():
    members = {'42': [dict(pack('A'), shortage_flag='0'), dict(pack('B'), shortage_flag='1')]}
    from triage import group_states
    rows = [{'NordicArticleNumber': 'A'}]
    alias = {'A': '42', 'B': '42'}
    assert group_states('2026-11-23', rows, members, alias, True) == {'42': True}      # the register's day: B is flagged short
    assert group_states('2026-11-22', rows, members, alias, False) == {'42': False}    # any other day: the dates make B an alternative


def test_market_flag_decides_a_package_without_an_entry_date_in_every_capture():
    """The public text says so: on_market reads the dates, and today's market flag only where there is no entry date."""
    assert on_market({'market': '1', 'entry': '', 'exit': ''}, '2026-01-01')
    assert not on_market({'market': '0', 'entry': '', 'exit': ''}, '2026-01-01')
