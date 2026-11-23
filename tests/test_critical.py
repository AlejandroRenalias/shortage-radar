import io
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


def product(atc, name='Name'):
    return {'atc': atc, 'name': name, 'strength': '1 mg', 'form': 'x', 'substances': 'Substance', 'pack': '1'}


def detail(route_ids, flag='1', form_id='16'):
    return {'routes': [(r, '') for r in route_ids], 'eu_flag': flag, 'form_id': form_id}


def match(atc, route_ids, flag='1'):
    return C.classify('012345', product(atc), detail(route_ids, flag), EU, ROUTES, FORMS)


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
    m = match('H01BA02', ['1070'], flag='0')
    assert m['match_type'] == 'route-mismatch' and m['list_row'] == 115 and 'under the tongue' in m['note']
    # Miochol-E 019235 is into the front chamber of the eye and Fimea's flag is 0: exact, with a note about the flag.
    m = match('S01EB09', ['1092'], flag='0')
    assert m['match_type'] == 'exact' and m['list_row'] == 382
    assert 'does not flag' in m['note'] and 'match the list' in m['note']


def test_atc_must_match_exactly_and_the_flag_only_cross_checks():
    assert match('A02BC051', ['1047'], flag='0') is None and match('A02BC06', ['1047'], flag='0') is None
    flagged = match('A02BC06', ['1047'], flag='1')
    assert flagged['match_type'] == 'flag-only' and 'not on the EU list' in flagged['note']
    assert match('A02BC05', ['1047'], flag='1')['note'] == 'The ATC code is on the list and the route fits.'
    assert 'Fimea flags' in match('A02BC05', ['1055'], flag='1')['note']


def test_vnr_missing_from_the_register_is_unmatched():
    m = C.classify('999999', None, {}, EU, ROUTES, FORMS)
    assert m['match_type'] == 'unmatched' and 'not in the Fimea register' in m['note']


def event(vnr, first, last, removed=None, first_after='2026-11-01', at_first=False, start='2026-11-02'):
    return {'NordicArticleNumber': vnr, 'UnavailableFrom': start, 'EndingDate': '2026-12-01', 'DateOfTheNotification': '2026-10-30', 'Company': 'Co',
            'first_seen': first, 'last_seen': last, 'removed_on': removed, 'listed_at_first_capture': at_first, 'first_seen_after': first_after}


def fixture():
    products = {'111111': product('A02BC05', 'Esomep'), '222222': product('H01BA02', 'Desmo'), '333333': product('A02BC05', 'Esomep2'), '444444': product('Z99ZZ99', 'Other')}
    details = {'111111': detail(['1047']), '222222': detail(['1070'], '0'), '333333': detail(['1047']), '444444': detail(['1055'], '0')}
    events = [event('111111', '2026-11-20', '2026-11-23'), event('222222', '2026-11-10', '2026-11-23'), event('333333', '2026-11-02', '2026-11-12', removed='2026-11-13'),
              event('444444', '2026-11-20', '2026-11-23'), event('555555', '2026-11-20', '2026-11-23')]
    return events, products, details


def test_join_counts_rows_and_unmatched():
    events, products, details = fixture()
    matches = C.match_all(events, products, details, EU, ROUTES, FORMS)
    assert set(matches) == {'111111', '222222', '333333', '555555'}   # 444444 is in the register but not on the list
    rows = C.current_rows(events, matches)
    assert [r['vnr'] for r in rows] == ['111111', '222222', '555555']   # exact, route-mismatch, unmatched; gone notices are not current
    counts = C.counts(rows)
    assert (counts['exact'], counts['route-mismatch'], counts['unmatched']) == (1, 1, 1)
    lines = list(C.csv_rows(rows, EU['meta']))
    assert lines[0][-3:] == ['Fimea EU-critical flag', 'note', 'source credit'] and lines[1][lines[0].index('list version')] == '2.1'
    data = C.json_data(rows, EU['meta'], {}, '2026-11-23')
    assert data['list']['version'] == '2.1' and len(data['matches']) == 3 and 'European Medicines Agency' in data['matches'][0]['source_credit']


def test_history_counts_notices_and_marks_what_is_last_seen():
    events, products, details = fixture()
    matches = C.match_all(events, products, details, EU, ROUTES, FORMS)
    history = C.history(events, matches)
    h = history['A02BC05']
    assert h['count'] == 2 and h['listed_now'] == 1 and h['gone'] == 1
    assert (h['measured'], h['days_min'], h['days_max']) == (1, 10, 10)
    assert next(n for n in h['notices'] if n['removed_on'])['last_seen'] == '2026-11-12'
    assert '' not in history   # unmatched VNRs have no code


def test_alerts_are_new_exact_matches_only():
    events, products, details = fixture()
    matches = C.match_all(events, products, details, EU, ROUTES, FORMS)
    snapshots = [('2026-11-01', [{'NordicArticleNumber': '999999'}]), ('2026-11-20', [{'NordicArticleNumber': '111111'}])]
    alerts = C.new_alerts(events, matches, snapshots, '2026-11-15')
    assert [e['NordicArticleNumber'] for e, _ in alerts] == ['111111']
    # Already listed in the capture before, or listed in the first capture: not new.
    events[0]['first_seen_after'] = '2026-11-20'
    assert C.new_alerts(events, matches, snapshots, '2026-11-15') == []
    first = event('111111', '2026-11-20', '2026-11-23', at_first=True)
    assert C.new_alerts([first], matches, snapshots, '2026-11-15') == []


def test_feeds_and_downloads_carry_the_match_and_the_credit(tmp_path):
    events, products, details = fixture()
    matches = C.match_all(events, products, details, EU, ROUTES, FORMS)
    alerts = C.new_alerts(events, matches, [('2026-11-01', [])], '2026-11-15')
    C.write_outputs(tmp_path, C.current_rows(events, matches), EU['meta'], {}, '2026-11-23', alerts)
    items = ET.parse(tmp_path / 'critical-feed.xml').getroot().findall('./channel/item')
    assert len(items) == 1 and 'A02BC05' in items[0].findtext('title') and 'Union list' in items[0].findtext('description')
    feed = json.loads((tmp_path / 'critical-feed.json').read_text(encoding='utf-8'))
    assert feed['version'].endswith('/1.1') and feed['items'][0]['tags'] == ['A02BC05', 'exact']
    assert json.loads((tmp_path / 'critical.json').read_text(encoding='utf-8'))['counts']['exact'] == 1
    assert (tmp_path / 'critical.csv').read_bytes().startswith(b'\xef\xbb\xbfVNR,')


def test_pages_cover_every_code_and_the_methods():
    events, products, details = fixture()
    matches = C.match_all(events, products, details, EU, ROUTES, FORMS)
    rows = C.current_rows(events, matches)
    out = render_critical({'eu': EU, 'rows': rows, 'counts': C.counts(rows), 'history': C.history(events, matches), 'archive_start': '2026-09-15',
                           'snapshot_date': '2026-11-23', 'source_metadata': {}})
    assert len(out) == 299 + 2
    page = out['critical.html']
    assert 'Critical medicines in Finland' in page and 'version 2.1' in page and page.count('<tr data-type=') == 3 and 'European Medicines Agency' in page
    assert 'Last seen 12 Nov 2026' in out['critical-A02BC05.html'] and 'Row in the EMA file' in out['critical-A02BC05.html']
    for needle in ('CC BY 4.0', 'legal-notice', '416337', '019235', 'has no history', 'estimates'):
        assert needle in out['critical-methods.html'], needle


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
