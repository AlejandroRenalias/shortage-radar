"""The EU pages in Finnish: every text has both languages, no key is dead, the Finnish row notes follow the English ones, and the page hides the other language."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import critical as C
import critical_charts as charts
import critical_pages as P
import test_critical as T
import test_wording_c as W
from critical_copy import COPY, TYPE_NAMES_FI, ATC_GROUPS_FI, ROUTE_NAMES_FI, STATUS_NAMES_FI, plain

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ''.join((ROOT / 'scripts' / n).read_text(encoding='utf-8') for n in ('critical_pages.py', 'critical_charts.py'))
# Keys that are built from a prefix and a variable (f'type.{k}', f'm.check.{i}'), and the plural forms picked by a count.
DYNAMIC = ('type.', 'm.check.', 'hist.earlier.', 'hist.shortage', 'step.time', 'impact.')
# Finnish texts that keep English words on purpose (EU-source names, file names, quoted source terms).
ENGLISH_ALLOWED = {'m.src.eu', 'm.lic.credit', 'm.src.shortage', 'm.src.register', 'm.src.forms', 'm.lic.ema', 'm.rule.ingredient', 'm.rule.route', 'm.check.1', 'm.check.4', 'm.check.6',
                   'm.rule.result', 'm.lim.3', 'm.lim.4', 'm.rule.ongoing'}
ENGLISH_WORDS = re.compile(r'\b(the|and|which|with|from|is|are|not|this|that|shortage|shortages|notice|captures?|package|packages|ongoing|details?)\b')


def test_every_key_has_both_languages_and_is_used():
    for key, pair in COPY.items():
        assert len(pair) == 2 and all(isinstance(x, str) for x in pair), key
        assert pair[1].strip(), key                       # a Finnish text for every key
        if key != 'source.english':
            assert pair[0].strip(), key
        used = f"'{key}'" in SOURCES or f'"{key}"' in SOURCES or key.startswith(DYNAMIC) or (key.endswith('.many') and (f"'{key[:-5]}'" in SOURCES or key[:-5].startswith('n.')))
        assert used, f'{key} is not used by the pages'


def test_the_finnish_text_holds_no_english_sentence():
    for key, (en, fi) in COPY.items():
        text = re.sub(r'<[^>]+>', ' ', fi)
        if key in ENGLISH_ALLOWED:
            continue
        found = ENGLISH_WORDS.findall(text.lower())
        assert not found, (key, found)
    for names in (TYPE_NAMES_FI, ATC_GROUPS_FI, ROUTE_NAMES_FI, STATUS_NAMES_FI):
        assert all(v.strip() for v in names.values())
    assert set(TYPE_NAMES_FI) == set(C.TYPE_NAMES) | {'flag-only'} and set(STATUS_NAMES_FI) == set(C.STATUS_NAMES)
    assert set(ATC_GROUPS_FI) == set(charts.ATC_GROUPS) and set(ROUTE_NAMES_FI) == set(charts.ROUTE_NAMES)


def test_the_finnish_site_terms_are_the_ones_the_site_uses():
    fi = COPY['advice.short'][1] + COPY['explained'][1] + COPY['impact.substitute'][1]
    assert 'Vaihtokelpoinen pakkaus löytyy aineistosta' in fi
    assert 'saatavuushäiriö' in ' '.join(v[1] for v in COPY.values())
    assert 'tilannekuva' in COPY['tile.nomatch'][1] and 'Fimea' in COPY['lead.list'][1]


def test_finnish_row_notes_follow_the_english_notes_of_every_case():
    ongoing = dict(status='ongoing', start='2026-11-20', end='2026-12-01', notified='2026-11-20', company='Co')
    records = [T.match('A02BC05', ['1047'], flag='1'), T.match('A02BC05', ['1047'], flag='0'), T.match('H01BA02', ['1070'], flag='0'), T.match('H01BA02', ['1070'], flag='1'),
               T.match('H01BA02', ['1070', '1055'], flag='1'), T.match('H01BA02', ['1065'], flag='0'), T.match('B05BB01', ['1047'], flag='1', substances=['Sodium chloride']),
               T.match('A02BC05', ['1047'], flag='0', substances=[]), C.classify('999999', None, {}, T.EU, T.ROUTES, T.FORMS, T.RULES),
               C.classify('999998', T.product('Z99ZZ99'), T.detail(['1055'], '1'), T.EU, T.ROUTES, T.FORMS, T.RULES)]
    kinds = {r['match_type'] for r in records}
    assert kinds == {'exact', 'route-mismatch', 'ingredient-mismatch', 'unmatched', 'flag-only'}
    assert any(r.get('route_status') == 'unclear' for r in records)
    for r in records:
        row = dict(r, **ongoing)
        assert P.note_text(row, 0) == r['note'], (P.note_text(row, 0), r['note'])      # the English text is the one critical.py writes
        fi = P.note_text(row, 1)
        assert fi and fi != r['note'] and not ENGLISH_WORDS.findall(fi.lower().replace('exact', '')), (fi, r['note'])


def test_every_route_label_has_a_finnish_name():
    for entry in C.load_routes()['routes'].values():
        assert P.ROUTE_FI[entry['en']] and not re.search(r'\b(Ophthalmic|Topical)\b', P.ROUTE_FI[entry['en']], re.I), entry['en']


def test_a_built_page_names_its_title_and_description_in_both_languages():
    for name, page in W.eu_pages().items():
        head = re.search(r'data-title-en="([^"]+)" data-title-fi="([^"]+)" data-desc-en="([^"]+)" data-desc-fi="([^"]+)"', page)
        assert head and head.group(1) != head.group(2) and head.group(3) != head.group(4), name
        assert '<script src="critical.js" defer></script>' in page, name      # every EU page loads the one script that swaps them


def test_options_placeholders_and_aria_labels_carry_both_languages():
    page = W.eu_pages()['critical.html']
    assert 'data-en="All matches" data-fi="Kaikki täsmäykset"' in page and 'data-fi-placeholder="Nimi, vaikuttava aine, ATC-koodi, yritys tai VNR"' in page
    assert 'data-en="Exact match" data-fi="Täsmällinen osuma"' in page and 'data-fi-aria-label="Saatavuushäiriöpakkausten sivut"' in page
    assert 'data-fi-aria-label="Lisätietoa: Täsmällinen osuma"' in page
    assert plain('tile.info', 1, label='X') == 'Lisätietoa: X'


def test_the_language_menu_decides_which_text_shows():
    css = (ROOT / 'site/style.css').read_text(encoding='utf-8')
    assert '.l-en,.l-fi{display:contents!important}' in css and 'html:not([lang="fi"]) .l-fi{display:none!important}' in css


def _page(name='critical.html'):
    return W.eu_pages()[name]


def test_the_estimated_end_label_is_in_the_row_markup_for_phones():
    page = _page()
    assert '<span class="eu-end-label"><span class="l-en" lang="en">Estimated end</span><span class="l-fi" lang="fi">Arvioitu päättyminen</span></span> <span class="eu-end">' in page
    css = (ROOT / 'site/style.css').read_text(encoding='utf-8')
    assert '::before{content:"Ends ' not in css and 'Päättyy' not in css      # the label is text in the page, not generated content
    assert '.eu-table .eu-end-label{display:none}' in css and '.eu-table .eu-end-label{display:inline' in css


def test_status_and_reported_start_are_separated_in_the_markup():
    page = _page()
    assert 'Ongoing <span class="note">reported start' in page and 'Käynnissä <span class="note">ilmoitettu alkamispäivä' in page


def test_the_route_chip_names_the_combined_group_and_the_actual_route_stays_in_details():
    assert charts.ROUTE_NAMES['oral'] == 'By mouth or under the tongue' and ROUTE_NAMES_FI['oral'] == 'Suun kautta tai kielen alle'
    assert 'Suun kautta tai kielen alle' in charts.route_label(['under the tongue']) and 'By mouth or under the tongue' in charts.route_label(['under the tongue'])


def test_methods_text_on_ingredients_and_example_count():
    methods = _page('critical-methods.html')
    assert 'Lisäaineet' not in methods and 'Valmisteessa voi olla myös muita vaikuttavia aineita' in methods
    assert 'B05BB01 is the ATC code for electrolytes, shared by the EU potassium chloride row' in methods and 'B05BB01 on elektrolyyttien ATC-koodi' in methods
    assert 'these four cases' not in methods and 'neljässä' not in methods and 'on these cases' in methods


def test_the_flag_total_covers_the_match_types_it_names():
    rows = [dict(status='ongoing', match_type=t, fimea_flag=f) for t, f in (('exact', '0'), ('exact', '1'), ('route-mismatch', '1'), ('ingredient-mismatch', '1'), ('ingredient-mismatch', '0'), ('unmatched', ''))]
    assert C.counts(rows)['disagree'] == 3      # exact with flag 0, route mismatch with flag 1, ingredient mismatch with flag 1
    assert 'ingredient not confirmed) for' in COPY['flag'][0] and 'vaikuttavaa ainetta ei vahvistettu) ' in COPY['flag'][1]


def test_rows_carry_the_verified_finnish_substance_words_for_the_search():
    events, products, details = T.fixture()
    matches = T.matches_of(events, products, details)
    rows = C.current_rows(events, matches)
    import critical_pages as P2
    html = P2.critical_page({'eu': T.EU, 'rows': rows, 'counts': C.counts(rows), 'history': {}, 'archive_start': '2026-09-15', 'snapshot_date': '2026-11-23', 'source_metadata': {},
                             'substance_fi': {'222222': 'desmopressiini'}})
    assert 'data-fi="desmopressiini"' in html and html.count('data-fi=""') == len(rows) - 1
    js = (ROOT / 'site/critical.js').read_text(encoding='utf-8')
    assert "searchMatches({substances: tr.dataset.text, substance_fi: tr.dataset.fi || ''}, input.value)" in js
