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
    assert 'html[lang="fi"] .eu-table td[data-label="Estimated end"]::before{content:"Päättyy "}' in css
