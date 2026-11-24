"""PR C wording: the EU pages explain "critical" and carry a Finnish block, old phrases are gone, and the credit says what `impact` is."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import critical as C
import test_critical as T
from build import fimea_credit
from changes import TEXT
from critical_copy import COPY
from critical_pages import render_critical
from pages import render_pages

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'site/i18n.js').read_text(encoding='utf-8')
OLD = ('Expected to become unavailable on', 'Fimea file changed', 'Fimean tiedosto muuttui', 'Later than estimated', 'Report date', 'None today', 'No notice on Fimea’s list today',
       'A pharmacist or doctor decides what you take', 'for a while', 'vähään aikaan', 'häiriöiseksi', 'suosittele', 'Notified</dt>')


def eu_pages():
    events, products, details = T.fixture()
    matches = T.matches_of(events, products, details)
    rows = C.current_rows(events, matches)
    return render_critical({'eu': T.EU, 'rows': rows, 'counts': C.counts(rows), 'history': C.history(events, matches, []), 'archive_start': '2026-09-15',
                            'snapshot_date': '2026-11-23', 'source_metadata': {}})


def test_old_phrases_are_gone_from_the_source_and_the_built_pages():
    sources = ''.join((ROOT / p).read_text(encoding='utf-8') for p in ('site/i18n.js', 'scripts/pages.py', 'scripts/critical_pages.py', 'scripts/critical.py', 'scripts/changes.py'))
    built = ''.join(render_pages(749).values()) + ''.join(eu_pages().values())
    for phrase in OLD:
        assert phrase not in sources + built, phrase


def visible_text(html, language):
    """The text of the page body that a visitor sees with the menu language `language`: the spans of the other language are left out."""
    from html.parser import HTMLParser
    other = 'l-en' if language == 'fi' else 'l-fi'

    class Reader(HTMLParser):
        def __init__(self):
            super().__init__()
            self.depth, self.skip, self.out = 0, None, []

        def handle_starttag(self, tag, attrs):
            if tag in ('br', 'link', 'meta', 'input', 'img', 'path', 'rect', 'circle', 'use'):
                return
            self.depth += 1
            if self.skip is None and other in dict(attrs).get('class', '').split():
                self.skip = self.depth

        def handle_endtag(self, tag):
            if tag in ('br', 'link', 'meta', 'input', 'img', 'path', 'rect', 'circle', 'use'):
                return
            if self.skip == self.depth:
                self.skip = None
            self.depth -= 1

        def handle_data(self, data):
            if self.skip is None:
                self.out.append(data)
    reader = Reader()
    reader.feed(html[html.index('<main'):html.index('</main>')])
    return ' '.join(' '.join(reader.out).split())


def test_eu_pages_explain_critical_in_both_languages_and_show_one_at_a_time():
    out = eu_pages()
    explained = 'The EU list names medicines whose continuous supply the EU treats as a priority. It does not rate how serious a shortage is for you.'
    explained_fi = 'EU:n luettelossa ovat lääkkeet, joiden jatkuvaa saatavuutta EU pitää ensisijaisen tärkeänä.'
    for name in ('critical.html', 'critical-A02BC05.html', 'critical-methods.html'):
        page = out[name]
        assert 'EU critical medicines list: shortages in Finland' in page and explained in page
        assert '‘Interchangeable package found in the data’ / ‘No interchangeable package found in the data’' in page
        assert explained_fi in page and 'EU:n kriittisten lääkkeiden luettelo: saatavuushäiriöt Suomessa' in page
    # The old Finnish block (shown in every language) and the "English only" notes are gone.
    for name, page in out.items():
        assert 'class="eu-fi"' not in page and 'Nämä sivut ovat englanniksi' not in page and 'in English only' not in page, name
    # The English view shows no Finnish text and the Finnish view no English sentence; the advice stays visible in both, in short form.
    for name, page in out.items():
        en, fi = visible_text(page, 'en'), visible_text(page, 'fi')
        assert 'Not medical advice. A listing does not show pharmacy stock.' in en and 'Ei lääketieteellinen neuvo. Listalla oleminen ei kerro apteekin varastosta.' in fi, name
        assert not re.search(r'Kysy apteekista|saatavuushäiriö|Nämä sivut|lääke', en), name
        assert not re.search(r'(Not medical advice|A listing does not|Details:|Shortage packages|Ongoing)', fi), name
    # The short line and the tiles come before the long text, which sits in closed "Details" folds.
    page = out['critical.html']
    assert page.index('eu-advice-short') < page.index('class="eu-tiles"') < page.index('<details class="eu-fold eu-notes">')
    assert '<details class="eu-fold eu-notes" open' not in page
    notes = page[page.index('<details class="eu-fold eu-notes">'):page.index('<details class="eu-fold eu-charts-fold"')]
    assert explained in notes and 'This is not medical advice.' in notes and 'EU list version 2.1.' in notes
    # The Finnish label names that the explanation gives are the impact chips of the site.
    fi_names = [re.findall(key + r': "([^"]+)"', JS)[1] for key in ('impactChip_substitute', 'impactChip_no_alternative')]
    assert COPY['impact.substitute'][1] == fi_names[0] and COPY['impact.no_alternative'][1] == fi_names[1]
    assert all(f'”{n}”' in out['critical.html'] for n in fi_names)


def test_code_page_without_a_notice_names_the_capture_not_today():
    out = eu_pages()
    empty = next(p for n, p in out.items() if n.startswith('critical-A') and 'No notice matched in the latest capture' in p)
    assert 'Capture of 23 Nov 2026. This does not show stock.' in empty and 'No notice was matched to this code in the latest capture (23 Nov 2026).' in empty
    assert 'Tähän koodiin ei yhdistetty Fimean ilmoitusta viimeisimmässä tilannekuvassa (23.11.2026). Tämä ei kerro varastosta.' in empty
    for old in ('None today', 'No notice on Fimea’s list today', 'on Fimea’s list today', 'tänään', 'Fimea lists no shortage', 'Status today', 'notices today'):
        assert old not in empty, old


def test_methods_page_explains_critical_in_english_and_finnish():
    methods = eu_pages()['critical-methods.html']
    assert 'The EU list names medicines whose continuous supply the EU treats as a priority. It does not rate how serious a shortage is for you.' in methods
    assert 'EU:n luettelossa ovat lääkkeet, joiden jatkuvaa saatavuutta EU pitää ensisijaisen tärkeänä. Luettelo ei kerro, kuinka vakava häiriö on sinulle' in methods


def test_date_labels_are_the_same_everywhere():
    assert re.search(r'\breported: "Notification date"', JS) and re.search(r'\bstarts: "Shortage expected to start on"', JS)
    page = eu_pages()['critical-A02BC05.html']
    assert '<dt><span class="l-en" lang="en">Notification date</span>' in page and '<dt><span class="l-en" lang="en">Reported start</span>' in page and 'Notified</' not in page
    assert TEXT['en']['notified'] == 'Notification date' and TEXT['en']['since'] == 'Reported start'


def test_the_finnish_feed_has_finnish_rights_text_and_the_english_feed_keeps_its_own():
    assert 'Fimea' in TEXT['fi']['rights'] and 'CC BY 4.0' in TEXT['fi']['rights'] and 'Data:' not in TEXT['fi']['rights'] and 'joined' not in TEXT['fi']['rights']
    assert TEXT['en']['rights'] == 'Data: Finnish Medicines Agency Fimea, CC BY 4.0. Selected, joined and transformed.'


def test_the_data_credit_says_impact_is_shortage_radars_reading():
    credit = fimea_credit({})
    assert 'impact' in credit and 'Shortage Radar' in credit and 'not a Fimea field' in credit
