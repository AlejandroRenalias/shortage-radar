import io
import re
from datetime import date, timedelta
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import critical as C
import fetch_critical
from critical_pages import render_critical

EU = C.load_eu_list()
ROUTES = C.load_routes()
FORMS = C.load_forms()


RULES = C.load_ingredient_rules()


def product(atc, name='Name', substances='Substance'):
    return {'atc': atc, 'name': name, 'strength': '1 mg', 'form': 'x', 'substances': substances, 'pack': '1'}


def detail(route_ids, flag='1', form_id='16', substances=None):
    return {'routes': [(r, '') for r in route_ids], 'eu_flag': flag, 'form_id': form_id, 'substances': substances if substances is not None else ['Substance']}


def match(atc, route_ids, flag='1', substances=None):
    """A match for a product with the ATC code and routes; the active ingredient is the list substance unless given."""
    if substances is None:
        substances = [EU['rows'][atc]['description'].title()] if atc in EU['rows'] else ['Other']
    return C.classify('012345', product(atc, substances=', '.join(substances)), detail(route_ids, flag, substances=substances), EU, ROUTES, FORMS, RULES)


def test_the_pinned_list_is_version_2_1_with_one_row_per_atc_code():
    assert EU['meta']['version'] == '2.1' and EU['meta']['reference'] == 'EMA/229885/2026'
    assert len(EU['rows']) == 299
    assert EU['rows']['H01BA02']['row'] == 115 and EU['rows']['S01EB09']['route'] == 'intraocular use'


def test_route_rule_uses_the_table_and_the_list_row():
    fits = lambda ids, route: C.route_fit([(i, '') for i in ids], route, ROUTES)[0]
    assert fits(['1070'], 'intramuscular use, intravenous use, subcutaneous use') == 'no'   # under the tongue
    assert fits(['1070'], 'sublingual use') == 'fits'
    assert fits(['1047', '1055'], 'oral use') == 'fits'                                      # one route of several is enough
    assert fits(['1092'], 'intraocular use') == 'fits'                                       # front chamber of the eye
    assert fits(['1053'], 'intraocular use') == 'no'                                         # eye surface is "ocular use"
    assert fits(['1069'], 'parenteral use') == 'fits' and fits(['1055'], 'parenteral use') == 'no'
    assert fits(['1047'], 'intravascular use') == 'fits'
    assert fits(['1002'], 'oral use') == 'no'                                                # known route with no EU term


def test_route_unclear_is_never_a_match():
    for ids in ([], ['1065'], ['9999']):
        assert C.route_fit([(i, '') for i in ids], 'oral use', ROUTES)[0] == 'unclear'
    m = match('A02BC05', [])
    assert m['match_type'] == 'route-mismatch' and m['route_status'] == 'unclear' and 'Route unclear' in m['note']


def test_the_four_rows_checked_by_hand():
    # Desmopressin 416337, 448525 and 485073 are sublingual: route-mismatch.
    m = match('H01BA02', ['1070'], flag='0', substances=['Desmopressin acetate'])
    assert m['match_type'] == 'route-mismatch' and m['list_row'] == 115 and 'under the tongue' in m['note']
    # Miochol-E 019235 is into the front chamber of the eye and Fimea's flag is 0: exact, with a note about the flag.
    m = match('S01EB09', ['1092'], flag='0', substances=['Acetylcholine chloride'])
    assert m['match_type'] == 'exact' and m['list_row'] == 382
    assert 'does not flag' in m['note'] and 'match the list' in m['note']


def test_atc_must_match_exactly_and_the_flag_only_cross_checks():
    assert match('A02BC051', ['1047'], flag='0') is None and match('A02BC06', ['1047'], flag='0') is None
    flagged = match('A02BC06', ['1047'], flag='1')
    assert flagged['match_type'] == 'flag-only' and 'not on the EU list' in flagged['note']
    assert match('A02BC05', ['1047'], flag='1')['note'] == 'The ATC code and the active ingredient are on the list and the route fits.'
    assert 'Fimea flags' in match('A02BC05', ['1055'], flag='1')['note']


def test_vnr_missing_from_the_register_is_unmatched():
    m = C.classify('999999', None, {}, EU, ROUTES, FORMS)
    assert m['match_type'] == 'unmatched' and 'not in the Fimea register' in m['note']


def test_sodium_chloride_does_not_match_the_potassium_chloride_entry():
    """VNR 389066 (B. Braun sodium chloride) has the ATC code B05BB01 of potassium chloride and a fitting route."""
    m = match('B05BB01', ['1047'], flag='0', substances=['Sodium chloride'])
    assert m['match_type'] == 'ingredient-mismatch' and m['route_status'] == 'fits'
    assert 'Sodium chloride' in m['note'] and 'Potassium Chloride' in m['note']
    assert match('B05BB01', ['1047'], substances=['Potassium chloride'])['match_type'] == 'exact'
    assert match('B05BB01', ['1047'], substances=['Sodium chloride', 'Potassium chloride'])['match_type'] == 'exact'   # combination with the list substance
    assert match('B05BB01', ['1047'], substances=[])['match_type'] == 'ingredient-mismatch'                            # no ingredients: not confirmed
    assert 'none given' in match('B05BB01', ['1047'], substances=[])['note']


def test_ingredient_check_by_name_and_for_combinations():
    fit = lambda description, *names: C.ingredient_fit(description, list(names), RULES)
    assert fit('IPRATROPIUM', 'Ipratropium bromide monohydrate') and fit('HEPARIN', 'Heparin sodium')
    assert not fit('POTASSIUM CHLORIDE', 'Sodium chloride') and not fit('METHOTREXATE', 'Methotrexatum')
    assert fit('PIPERACILLIN, TAZOBACTAM', 'Piperacillin sodium', 'Tazobactam sodium')
    assert not fit('PIPERACILLIN, TAZOBACTAM', 'Piperacillin sodium')                       # every substance of the list row is needed
    assert fit('EPINEPHRINE', 'Adrenaline tartrate') and not fit('EPINEPHRINE', 'Noradrenaline tartrate')
    assert fit('NOREPINEPHRINE', 'Noradrenaline tartrate')
    assert fit('INFLUENZA VACCINE (various forms, strains)', 'Influenza A virus H1N1, split virion, inactivated')
    assert not fit('INFLUENZA VACCINE (various forms, strains)', 'Hepatitis B virus, surface antigen, rDNA')
    assert not fit('ATROPINE')                                                              # no ingredients given


def test_every_code_with_shortages_today_keeps_its_exact_matches():
    """The ingredient check removed exactly one of the 92 exact matches of 23 Nov 2026 (389066); these real names still pass."""
    for atc, names in {'S01EB09': ['Acetylcholine chloride'], 'A03BA01': ['Atropine sulfate'], 'C01CA24': ['Adrenaline'], 'V03AF03': ['Calcium folinate'],
                       'J01EE01': ['Trimethoprim', 'Sulfamethoxazole'], 'N03AG01': ['Sodium valproate', 'Valproic acid'], 'L01XX05': ['Hydroxyurea'], 'B02BD02': ['Turoctocog alfa']}.items():
        assert C.ingredient_fit(EU['rows'][atc]['description'], names, RULES), atc


def event(vnr, first, last, removed=None, first_after=None, at_first=False, start='2026-11-02', valid='K', notified='2026-10-30', end='2026-12-01', edited=False):
    first_after = first_after or (date.fromisoformat(first) - timedelta(days=1)).isoformat()   # by default the capture before is a day earlier
    return {'NordicArticleNumber': vnr, 'Valid': valid, 'UnavailableFrom': start, 'EndingDate': end, 'DateOfTheNotification': notified, 'Company': 'Co',
            'first_seen': first, 'last_seen': last, 'removed_on': removed, 'listed_at_first_capture': at_first, 'first_seen_after': first_after, 'vnr_listed_at_removal': edited}


def fixture():
    products = {'111111': product('A02BC05', 'Esomep', 'Esomeprazole'), '222222': product('H01BA02', 'Desmo', 'Desmopressin acetate'), '333333': product('A02BC05', 'Esomep2', 'Esomeprazole'),
                '444444': product('Z99ZZ99', 'Other'), '666666': product('B05BB01', 'Natrium', 'Sodium chloride')}
    details = {'111111': detail(['1047'], substances=['Esomeprazole']), '222222': detail(['1070'], '0', substances=['Desmopressin acetate']),
               '333333': detail(['1047'], substances=['Esomeprazole']), '444444': detail(['1055'], '0'), '666666': detail(['1047'], '0', substances=['Sodium chloride'])}
    events = [event('111111', '2026-11-20', '2026-11-23'), event('222222', '2026-11-10', '2026-11-23'), event('333333', '2026-11-02', '2026-11-12', removed='2026-11-13'),
              event('444444', '2026-11-20', '2026-11-23'), event('555555', '2026-11-20', '2026-11-23'), event('666666', '2026-11-20', '2026-11-23')]
    return events, products, details


def matches_of(events, products, details):
    return C.match_all(events, products, details, EU, ROUTES, FORMS, RULES)


def test_join_counts_rows_and_unmatched():
    events, products, details = fixture()
    matches = matches_of(events, products, details)
    assert set(matches) == {'111111', '222222', '333333', '555555', '666666'}   # 444444 is in the register but not on the list
    rows = C.current_rows(events, matches)
    assert [r['vnr'] for r in rows] == ['111111', '222222', '666666', '555555']   # exact, route-mismatch, ingredient, unmatched; gone notices are not current
    ongoing = C.counts(rows)['ongoing']
    assert (ongoing['exact'], ongoing['route-mismatch'], ongoing['ingredient-mismatch'], ongoing['unmatched']) == (1, 1, 1, 1)
    lines = list(C.csv_rows(rows, EU['meta']))
    assert lines[0][-3:] == ['Fimea EU-critical flag', 'note', 'source credit'] and lines[1][lines[0].index('list version')] == '2.1'
    assert lines[1][lines[0].index('status')] == 'ongoing'
    data = C.json_data(rows, EU['meta'], {}, '2026-11-23')
    assert data['list']['version'] == '2.1' and len(data['matches']) == 4 and data['snapshot_date'] == '2026-11-23'
    assert 'European Medicines Agency' in data['matches'][0]['source_credit']


def test_upcoming_notices_are_counted_apart_from_ongoing_ones():
    """Fimea Voimassa K is ongoing, E has not started yet; two exact matches started on 30 Nov and 7 Dec."""
    events, products, details = fixture()
    events += [event('111112', '2026-11-20', '2026-11-23', valid='E', start='2026-11-30'), event('111113', '2026-11-20', '2026-11-23', valid='E', start='2026-12-07')]
    products.update({'111112': product('A02BC05', 'Esomep3', 'Esomeprazole'), '111113': product('A02BC05', 'Esomep4', 'Esomeprazole')})
    details.update({'111112': detail(['1047'], substances=['Esomeprazole']), '111113': detail(['1047'], substances=['Esomeprazole'])})
    rows = C.current_rows(events, matches_of(events, products, details))
    counts = C.counts(rows)
    assert counts['ongoing']['exact'] == 1 and counts['upcoming']['exact'] == 2
    assert [r['status'] for r in rows if r['match_type'] == 'exact'] == ['ongoing', 'upcoming', 'upcoming']   # ongoing first
    page = render_critical({'eu': EU, 'rows': rows, 'counts': counts, 'history': {}, 'archive_start': '2026-09-15', 'snapshot_date': '2026-11-23', 'source_metadata': {}})['critical.html']
    assert 'Fimea file saved' in page and '>23 Nov 2026<' in page and 'Starts later' in page and 'on 30 Nov 2026' in page and 'on 7 Dec 2026' in page
    assert 'Starts later.' in page and 'has not started yet (2 exact match' in page and '2 more start later.' in page
    assert 'data-status="upcoming"' in page and 'id="eu-status"' in page


def test_history_counts_shortages_and_marks_what_is_last_seen():
    events, products, details = fixture()
    matches = matches_of(events, products, details)
    history = C.history(events, matches, ['2026-11-02', '2026-11-12', '2026-11-13', '2026-11-20', '2026-11-23'])
    h = history['A02BC05']
    assert h['count'] == 2 and h['listed_now'] == 1 and h['gone'] == 1
    assert (h['measured'], h['days_min'], h['days_max']) == (1, 10, 10)
    assert next(n for n in h['notices'] if n['removed_on'])['last_seen'] == '2026-11-12'
    assert '' not in history   # unmatched VNRs have no code


def test_an_edited_notice_is_one_shortage():
    """Changing the start or notification date shows in the archive as a removal and a new notice in the same capture."""
    first = event('111111', '2026-11-02', '2026-11-09', removed='2026-11-10', edited=True)
    second = event('111111', '2026-11-10', '2026-11-23', first_after='2026-11-09', start='2026-11-05', notified='2026-11-09', end='2026-12-20')
    merged = C.shortages([second, first], ['2026-11-02', '2026-11-09', '2026-11-10', '2026-11-23'])
    assert len(merged) == 1
    n = merged[0]
    assert (n['edits'], n['first_seen'], n['last_seen'], n['removed_on']) == (1, '2026-11-02', '2026-11-23', None)
    assert n['EndingDate'] == '2026-12-20' and n['UnavailableFrom'] == '2026-11-05'       # the latest values
    events, products, details = fixture()
    matches = matches_of([first, second], products, details)
    assert C.history([first, second], matches, ['2026-11-02', '2026-11-23'])['A02BC05']['count'] == 1
    # Two notices of one VNR that are not an edit stay two shortages.
    other = event('111111', '2026-11-15', '2026-11-23', start='2026-11-14', notified='2026-11-14')
    assert len(C.shortages([event('111111', '2026-11-02', '2026-11-12', removed='2026-11-13'), other], [])) == 2


def test_a_gap_in_the_captures_is_unknown_not_a_new_start():
    gone = event('111111', '2026-11-02', '2026-11-05', removed='2026-11-06')
    back = event('111111', '2026-11-09', '2026-11-12', first_after='2026-11-06')   # same notice after one missing capture
    merged = C.shortages([gone, back], ['2026-11-02', '2026-11-05', '2026-11-06', '2026-11-09', '2026-11-12'])
    assert len(merged) == 1 and merged[0]['unseen'] == [{'from': '2026-11-05', 'to': '2026-11-09'}] and merged[0]['first_seen'] == '2026-11-02'
    # A long stretch without captures inside a shortage is a gap, and the length is left out of the statistics.
    long = event('333333', '2026-09-15', '2026-11-12', removed='2026-11-13')
    n = C.shortages([long], ['2026-09-15', '2026-11-12', '2026-11-13'])[0]
    assert n['gaps'] == [{'from': '2026-09-15', 'to': '2026-11-12', 'days': 58}]
    events, products, details = fixture()
    matches = matches_of([long], products, details)
    h = C.history([long], matches, ['2026-09-15', '2026-11-12', '2026-11-13'])['A02BC05']
    assert h['measured'] == 0 and h['days_median'] is None
    row = [r for r in C.history([long], matches, ['2026-09-15', '2026-11-12', '2026-11-13'])['A02BC05']['notices']][0]
    assert row['gaps']
    page = render_critical({'eu': EU, 'rows': [], 'counts': C.counts([]), 'history': C.history([long], matches, ['2026-09-15', '2026-11-12', '2026-11-13']),
                            'archive_start': '2026-09-15', 'snapshot_date': '2026-11-23', 'source_metadata': {}})['critical-A02BC05.html']
    assert 'Days between captures' in page and 'unknown' in page and 'Last seen 12 Nov 2026' in page and 'Days between</th>' not in page


def test_alerts_are_new_exact_matches_only():
    events, products, details = fixture()
    matches = matches_of(events, products, details)
    snapshots = [('2026-11-01', [{'NordicArticleNumber': '999999'}]), ('2026-11-20', [{'NordicArticleNumber': '111111'}])]
    alerts = C.new_alerts(events, matches, snapshots, '2026-11-15')
    assert [n['NordicArticleNumber'] for n, _ in alerts] == ['111111']     # 666666 is an ingredient mismatch and is not an alert
    # Already listed in the capture before, or listed in the first capture: not new.
    events[0]['first_seen_after'] = '2026-11-20'
    assert C.new_alerts(events, matches, snapshots, '2026-11-15') == []
    first = event('111111', '2026-11-20', '2026-11-23', at_first=True)
    assert C.new_alerts([first], matches, snapshots, '2026-11-15') == []


def test_alert_id_is_stable_when_a_notice_vanishes_for_one_capture_and_returns(tmp_path):
    gone = event('111111', '2026-11-16', '2026-11-17', removed='2026-11-18')
    back = event('111111', '2026-11-20', '2026-11-23', first_after='2026-11-18')
    events, products, details = fixture()
    matches = matches_of([gone, back], products, details)
    snapshots = [('2026-11-15', []), ('2026-11-16', []), ('2026-11-17', []), ('2026-11-18', []), ('2026-11-20', []), ('2026-11-23', [])]
    alerts = C.new_alerts([gone, back], matches, snapshots, '2026-11-10')
    assert len(alerts) == 1 and alerts[0][0]['first_seen'] == '2026-11-16'          # the return is not a new shortage
    # Even if the same shortage reaches the feed twice, the id is the same and the feed keeps one entry.
    twice = alerts + alerts
    items = C.alert_items(twice, EU['meta'])
    assert len(items) == 1 and items[0]['id'] == C.alert_item(alerts[0][0], alerts[0][1], EU['meta'])['id']
    C.write_outputs(tmp_path, [], EU['meta'], {}, '2026-11-23', twice)
    rss_ids = [g.text for g in ET.parse(tmp_path / 'critical-feed.xml').getroot().iter('guid')]
    json_ids = [i['id'] for i in json.loads((tmp_path / 'critical-feed.json').read_text(encoding='utf-8'))['items']]
    assert len(rss_ids) == 1 and rss_ids == json_ids
    # An edit of the notice later does not change the id.
    edited = dict(alerts[0][0], UnavailableFrom='2026-12-01', EndingDate='2027-01-01')
    assert C.alert_item(edited, alerts[0][1], EU['meta'])['id'] == items[0]['id']


def test_upcoming_alerts_say_so():
    events, products, details = fixture()
    events.append(event('111111', '2026-11-22', '2026-11-23', first_after='2026-11-20', valid='E', start='2026-11-30'))
    events.remove(events[0])
    matches = matches_of(events, products, details)
    (n, m), = C.new_alerts(events, matches, [('2026-11-20', [])], '2026-11-15')
    item = C.alert_item(n, m, EU['meta'])
    assert item['title'].startswith('New upcoming shortage') and 'not started yet' in item['text']


def test_feeds_and_downloads_carry_the_match_and_the_credit(tmp_path):
    events, products, details = fixture()
    matches = matches_of(events, products, details)
    alerts = C.new_alerts(events, matches, [('2026-11-01', [])], '2026-11-15')
    C.write_outputs(tmp_path, C.current_rows(events, matches), EU['meta'], {}, '2026-11-23', alerts)
    items = ET.parse(tmp_path / 'critical-feed.xml').getroot().findall('./channel/item')
    assert len(items) == 1 and 'A02BC05' in items[0].findtext('title') and 'Union list' in items[0].findtext('description')
    feed = json.loads((tmp_path / 'critical-feed.json').read_text(encoding='utf-8'))
    assert feed['version'].endswith('/1.1') and feed['items'][0]['tags'] == ['A02BC05', 'exact']
    assert json.loads((tmp_path / 'critical.json').read_text(encoding='utf-8'))['counts']['ongoing']['exact'] == 1
    assert (tmp_path / 'critical.csv').read_bytes().startswith(b'\xef\xbb\xbfVNR,')


def test_pages_cover_every_code_and_the_methods():
    events, products, details = fixture()
    matches = matches_of(events, products, details)
    rows = C.current_rows(events, matches)
    out = render_critical({'eu': EU, 'rows': rows, 'counts': C.counts(rows), 'history': C.history(events, matches, []), 'archive_start': '2026-09-15',
                           'snapshot_date': '2026-11-23', 'source_metadata': {}})
    assert len(out) == 299 + 2
    page = out['critical.html']
    assert 'Critical medicines in Finland' in page and 'version 2.1' in page and page.count('<tr data-type=') == 4 and 'European Medicines Agency' in page
    assert 'Last seen 12 Nov 2026' in out['critical-A02BC05.html'] and 'Row in the EMA file' in out['critical-A02BC05.html']
    for needle in ('CC BY 4.0', 'legal-notice', '416337', '019235', 'has no history', 'estimates', 'Ingredient not confirmed', '389066', 'Voimassa K', 'days between captures'):
        assert needle in out['critical-methods.html'], needle


def test_the_ema_source_link_on_the_methods_page_is_the_list_page():
    events, products, details = fixture()
    methods = render_critical({'eu': EU, 'rows': [], 'counts': C.counts([]), 'history': {}, 'archive_start': '2026-09-15', 'snapshot_date': '2026-11-23', 'source_metadata': {}})['critical-methods.html']
    assert ('href="https://www.ema.europa.eu/en/human-regulatory-overview/post-authorisation/medicine-shortages-availability-issues/'
            'availability-medicines-during-crises/union-list-critical-medicines"') in methods
    assert 'medicine-shortages-and-availability-issues' not in methods


def workbook(rows):
    shared = []
    def s(text):
        shared.append(text)
        return len(shared) - 1
    sheet = [f'<row r="8"><c r="A8" t="s"><v>{s("EMA/1/2026")}</v></c></row>', '<row r="9"><c r="A9"><v>46330</v></c></row>',
             f'<row r="11"><c r="A11" t="s"><v>{s("Union list of critical medicines - version 9.9")}</v></c></row>',
             f'<row r="14"><c r="A14" t="s"><v>{s("ATC level 5")}</v></c><c r="B14" t="s"><v>{s("ATC description" + chr(10) + "long text")}</v></c>'
             f'<c r="C14" t="s"><v>{s("Route of administration")}</v></c><c r="D14" t="s"><v>{s("Date of inclusion")}</v></c></row>',
             f'<row r="15"><c r="B15" t="s"><v>{s("A - Alimentary tract")}</v></c></row>']
    for i, (atc, desc, route) in enumerate(rows):
        r = 16 + i
        sheet.append(f'<row r="{r}"><c r="A{r}" t="s"><v>{s(atc)}</v></c><c r="B{r}" t="s"><v>{s(desc)}</v></c><c r="C{r}" t="s"><v>{s(route)}</v></c><c r="D{r}"><v>45261</v></c></row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('xl/sharedStrings.xml', f'<sst {ns}>' + ''.join(f'<si><t>{t}</t></si>' for t in shared) + '</sst>')
        z.writestr('xl/worksheets/sheet1.xml', f'<worksheet {ns}><sheetData>' + ''.join(sheet) + '</sheetData></worksheet>')
    return buf.getvalue()


def test_workbook_reader_keeps_rows_version_and_source_row():
    rows = [(f'{chr(65 + i // 100)}{i % 100:02d}AA01', f'DRUG{i}', 'oral use') for i in range(300)]
    parsed = fetch_critical.read_workbook(workbook(rows))
    assert parsed['meta'] == {'title': 'Union list of critical medicines - version 9.9', 'version': '9.9', 'reference': 'EMA/1/2026', 'published': '2026-11-04'}
    assert len(parsed['rows']) == 300 and parsed['rows'][0]['row'] == 16 and parsed['rows'][0]['included'] == '2023-12-01'
    with pytest.raises(ValueError):
        fetch_critical.read_workbook(workbook(rows[:10]))


def test_route_table_blood_vessel_and_parenteral_rules():
    fits = lambda ids, route: C.route_fit([(i, '') for i in ids], route, ROUTES)[0]
    assert fits(['1030'], 'intravascular use') == 'fits' and fits(['1030'], 'intracoronary use') == 'fits'   # coronary artery
    assert fits(['1047'], 'intravascular use') == 'fits' and fits(['1023'], 'intravascular use') == 'fits'
    assert fits(['1080'], 'parenteral use') == 'fits'                                   # implantation
    assert fits(['1047'], 'parenteral use') == 'fits' and fits(['1038'], 'parenteral use') == 'fits'   # infusion and injection routes
    assert fits(['1033'], 'parenteral use') == 'no'                                     # a lesion application is not assumed to be an injection
    assert fits(['1002'], 'parenteral use') == 'no' and fits(['1055'], 'parenteral use') == 'no'
    assert ROUTES['routes']['1033']['parenteral'] is False and ROUTES['routes']['1080']['parenteral'] is True


def test_named_cases_389066_and_the_minirin_packs():
    """389066 sodium chloride has the potassium chloride code; Minirin 022246 and 022288 are by mouth in the register (sublingual in the product information)."""
    products = {'389066': product('B05BB01', 'Natriumklorid B. Braun', 'Sodium chloride'), '022246': product('H01BA02', 'Minirin', 'Desmopressin acetate'),
                '022288': product('H01BA02', 'Minirin', 'Desmopressin acetate'), '456491': product('H01BA02', 'Minirin', 'Desmopressin acetate')}
    details = {'389066': detail(['1047'], '0', substances=['Sodium chloride']), '022246': detail(['1055'], '0', substances=['Desmopressin acetate']),
               '022288': detail(['1055'], '0', substances=['Desmopressin acetate']), '456491': detail(['1051'], '0', substances=['Desmopressin acetate'])}
    events = [event(v, '2026-11-20', '2026-11-23') for v in products]
    matches = matches_of(events, products, details)
    assert matches['389066']['match_type'] == 'ingredient-mismatch'
    assert [matches[v]['match_type'] for v in ('022246', '022288', '456491')] == ['route-mismatch'] * 3
    assert C.new_alerts(events, matches, [('2026-11-01', [])], '2026-11-15') == []


SOURCES = {'shortages_last_modified': 'Sun, 22 Nov 2026 23:20:01 GMT', 'register_last_modified': 'Mon, 23 Nov 2026 00:31:00 GMT'}


def credit_ok(text):
    for needle in ('European Medicines Agency', 'EMA', 'version 2.1', 'Shortages.txt', 'Perusrekisteri2026.xml', 'https://creativecommons.org/licenses/by/4.0/', 'CC BY 4.0',
                   'Sun, 22 Nov 2026 23:20:01 GMT', 'Mon, 23 Nov 2026 00:31:00 GMT', 'file modification time', 'HTTP Last-Modified', 'changed the data'):
        assert needle in text, needle


def test_every_download_and_feed_carries_the_ema_and_fimea_credit(tmp_path):
    events, products, details = fixture()
    matches = matches_of(events, products, details)
    alerts = C.new_alerts(events, matches, [('2026-11-01', [])], '2026-11-15')
    assert alerts
    C.write_outputs(tmp_path, C.current_rows(events, matches), EU['meta'], SOURCES, '2026-11-23', alerts)
    import csv as csvmod
    with (tmp_path / 'critical.csv').open(encoding='utf-8-sig', newline='') as f:
        csv_rows = list(csvmod.DictReader(f))
    assert csv_rows and all(r['source credit'] for r in csv_rows)
    for r in csv_rows:
        credit_ok(r['source credit'])
    data = json.loads((tmp_path / 'critical.json').read_text(encoding='utf-8'))
    credit_ok(data['source_credit'])
    assert all(m['source_credit'] == data['source_credit'] for m in data['matches'])
    assert data['sources']['ema']['credit'] == 'European Medicines Agency (EMA)' and data['sources']['fimea']['licence_url'].endswith('/by/4.0/')
    assert [f['file_modified'] for f in data['sources']['fimea']['files']] == [SOURCES['shortages_last_modified'], SOURCES['register_last_modified']]
    channel = ET.parse(tmp_path / 'critical-feed.xml').getroot().find('channel')
    credit_ok(channel.findtext('copyright'))
    for item in channel.findall('item'):
        credit_ok(item.findtext('description'))
    feed = json.loads((tmp_path / 'critical-feed.json').read_text(encoding='utf-8'))
    credit_ok(feed['_credit'])
    for item in feed['items']:
        credit_ok(item['content_text'])
    # Without recorded times the credit says so and does not invent them.
    assert 'file modification time not recorded' in C.credit(EU['meta'])


def test_english_content_is_marked_lang_en_whatever_language_the_menu_has():
    events, products, details = fixture()
    matches = matches_of(events, products, details)
    out = render_critical({'eu': EU, 'rows': C.current_rows(events, matches), 'counts': C.counts(C.current_rows(events, matches)), 'history': C.history(events, matches, []),
                           'archive_start': '2026-09-15', 'snapshot_date': '2026-11-23', 'source_metadata': SOURCES})
    for name in ('critical.html', 'critical-methods.html', 'critical-A02BC05.html'):
        html = out[name]
        main = html[html.index('<main'):html.index('</main>')]
        assert '<div lang="en">' in main and main.index('<div lang="en">') < main.index('<h1'), name
        credit_ok(html) if name != 'critical-methods.html' else None
    script = (Path(__file__).resolve().parents[1] / 'site/critical.js').read_text(encoding='utf-8')
    assert 'documentElement.lang' not in script       # the page language stays what the visitor chose; only the content is English
    css = (Path(__file__).resolve().parents[1] / 'site/style.css').read_text(encoding='utf-8')
    assert '.eu-table td>span{min-width:0;overflow-wrap:break-word}' in css


def test_mitomycin_start_after_a_666_day_gap_is_unknown():
    """Mitomycin (L01DC03) was first seen on 15 Sep 2026; the capture before it is from 18 Nov 2024, 666 days earlier."""
    assert (date(2026, 9, 15) - date(2024, 11, 18)).days == 666
    mito = event('777777', '2026-09-15', '2026-10-20', removed='2026-10-23', first_after='2024-11-18')
    close = event('777778', '2026-11-10', '2026-11-20', removed='2026-11-21', first_after='2026-11-06')
    days = ['2024-11-18', '2026-09-15', '2026-10-20', '2026-10-23', '2026-11-06', '2026-11-10', '2026-11-20', '2026-11-21']
    long_gap, near = C.shortages([mito, close], days)[0], C.shortages([close], days)[0]
    assert long_gap['start_unknown'] and long_gap['start_gap_days'] == 666
    assert not near['start_unknown'] and near['start_gap_days'] == 4
    # The threshold is "more than 14 days".
    on_edge = event('777779', '2026-11-20', '2026-11-21', first_after='2026-11-06')
    over = event('777780', '2026-11-21', '2026-11-21', first_after='2026-11-06')
    assert not C.shortages([on_edge], [])[0]['start_unknown'] and C.shortages([over], [])[0]['start_unknown']
    products = {'777777': product('L01DC03', 'Mitomycin medac', 'Mitomycin'), '777778': product('L01DC03', 'Mitomycin other', 'Mitomycin')}
    details = {v: detail(['1047'], substances=['Mitomycin']) for v in products}
    matches = matches_of([mito, close], products, details)
    h = C.history([mito, close], matches, days)['L01DC03']
    # Only the shortage with a known start is in the summary of lengths: 10 days, not 35.
    assert (h['count'], h['measured'], h['days_min'], h['days_max']) == (2, 1, 10, 10)
    page = render_critical({'eu': EU, 'rows': [], 'counts': C.counts([]), 'history': {'L01DC03': h}, 'archive_start': '2024-11-18', 'snapshot_date': '2026-11-23', 'source_metadata': {}})
    html = page['critical-L01DC03.html']
    assert 'Start unknown: no capture for 666 days before it.' in html and 'whose start we know' in html
    assert 'more than 14 days' in page['critical-methods.html']
    # A shortage first seen after a long gap is not a new alert.
    events = [dict(mito, removed_on=None, first_seen='2026-11-20', first_seen_after='2026-09-20')]
    assert C.new_alerts(events, matches, [('2026-09-20', [])], '2026-11-15') == []


def _two_row_page_data(rows):
    return {'eu': EU, 'rows': rows, 'counts': C.counts(rows), 'history': {}, 'archive_start': '2026-09-15', 'snapshot_date': '2026-11-23', 'source_metadata': {}}


def test_headline_tile_and_atc_chart_count_exact_matches_only():
    events, products, details = fixture()
    products['111120'], details['111120'] = product('A02BC05', 'Esomep9', 'Esomeprazole'), detail(['1055'], substances=['Esomeprazole'])   # route does not fit
    events.append(event('111120', '2026-11-20', '2026-11-23'))
    rows = C.current_rows(events, matches_of(events, products, details))
    counts = C.counts(rows)
    checked, exact = sum(counts['ongoing'][t] for t in C.TYPES), counts['ongoing']['exact']
    assert checked > exact > 0
    page = render_critical(_two_row_page_data(rows))['critical.html']
    assert f'<span class="eu-num">{exact:,}</span><span class="eu-tile-label">Exact match</span>' in page      # a box keeps the number and a short label
    assert f'Of {checked:,} ongoing packages checked' in page and 'class="eu-info"' in page                 # the longer text sits behind the "i"
    groups = page[page.index('<caption>Exact matches by ATC group'):]
    groups = groups[:groups.index('</table>')]
    assert sum(int(m) for m in re.findall(r'<td>(\d+)</td>', groups)) == exact     # ongoing and starts-later columns add up to the exact matches


def test_route_icon_uses_the_real_route_group():
    import critical_charts as charts
    assert charts.route_kind(['into the front chamber of the eye']) == 'eye'      # Miochol-E, 019235
    assert charts.route_kind(['into a vein', 'into a muscle']) == 'injection'
    assert charts.route_kind(['by mouth']) == 'oral' and charts.route_kind(['in the nose']) == 'other'
    assert charts.route_kind(['into a vein', 'by mouth']) == 'other' and charts.route_kind([]) == 'other'
    assert 'Injection' not in charts.route_label(['into the front chamber of the eye']) and 'Into the eye' in charts.route_label(['into the front chamber of the eye'])
    rows = [{'status': 'ongoing', 'match_type': 'exact', 'product_routes': ['into the front chamber of the eye']}, {'status': 'ongoing', 'match_type': 'route-mismatch', 'product_routes': ['by mouth']}]
    assert charts.route_counts(rows) == {'injection': 0, 'oral': 0, 'eye': 1, 'other': 0}


def test_timeline_strip_hatches_a_notice_that_vanished_for_a_capture():
    import critical_charts as charts
    n = {'name': 'Esomep', 'strength': '', 'first_seen': '2026-09-15', 'last_seen': '2026-11-20', 'removed_on': None, 'listed_at_first_capture': False, 'start_unknown': False,
         'gaps': [], 'unseen': [{'from': '2026-10-01', 'to': '2026-10-10'}]}
    svg = charts.timeline_strip([n], '2026-09-15', '2026-11-23')
    assert svg.count('class="eu-tl-gap"><title>') == 1     # the legend swatch has the class too, but no title
    assert 'Not listed in the captures 2026-10-01 to 2026-10-10: unknown' in svg
    steady = dict(n, unseen=[])
    assert 'class="eu-tl-gap"><title>' not in charts.timeline_strip([steady], '2026-09-15', '2026-11-23')


def test_long_urls_wrap_in_the_notes_and_other_credit_text():
    css = (Path(__file__).resolve().parents[1] / 'site/style.css').read_text(encoding='utf-8')
    assert '.eu-notes,.eu-info-text,.eu-list,.eu-more,.eu-code-page,.eu-facts{overflow-wrap:anywhere}' in css
