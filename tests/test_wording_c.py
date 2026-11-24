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
from critical_pages import FI_EXPLAINED, FI_NOTE, render_critical
from pages import render_pages

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'site/i18n.js').read_text(encoding='utf-8')
OLD = ('Expected to become unavailable on', 'Fimea file changed', 'Fimean tiedosto muuttui', 'Later than estimated', 'Report date', 'None today',
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


def test_eu_pages_explain_critical_and_have_a_finnish_block():
    out = eu_pages()
    explained = 'The EU list names medicines whose continuous supply the EU treats as a priority. It does not rate how serious a shortage is for you.'
    for name in ('critical.html', 'critical-A02BC05.html'):
        page = out[name]
        assert 'EU critical medicines list: shortages in Finland' in page and explained in page
        assert '‘Interchangeable package found in the data’ / ‘No interchangeable package found in the data’' in page
        assert FI_EXPLAINED in page and 'EU:n kriittisten lääkkeiden luettelo: saatavuushäiriöt Suomessa' in page
    for name, page in out.items():
        assert page.count('class="eu-fi" lang="fi"') == 1, name
        assert 'Nämä sivut ovat englanniksi.' in page and 'Kysy apteekista tai lääkäriltä.' in page, name
    assert out['critical.html'].index('eu-fi') < out['critical.html'].index('eu-counts-title')
    # The Finnish label names in the block are the ones the site uses.
    for key in ('impactChip_substitute', 'impactChip_no_alternative'):
        assert re.findall(key + r': "([^"]+)"', JS)[1] in FI_EXPLAINED


def test_code_page_without_a_notice_does_not_read_as_no_shortage():
    out = eu_pages()
    empty = next(p for n, p in out.items() if n.startswith('critical-A') and 'No notice on Fimea’s list today' in p)
    assert 'This does not show stock.' in empty and 'Fimean listalla ei ole tänään ilmoitusta' in empty
    assert 'None today' not in empty and 'Fimea lists no shortage for this code' not in empty


def test_date_labels_are_the_same_everywhere():
    assert re.search(r'\breported: "Notification date"', JS) and re.search(r'\bstarts: "Shortage expected to start on"', JS)
    page = eu_pages()['critical-A02BC05.html']
    assert '<dt>Notification date</dt>' in page and '<dt>Reported start</dt>' in page and '<dt>Notified</dt>' not in page
    assert TEXT['en']['notified'] == 'Notification date' and TEXT['en']['since'] == 'Reported start'


def test_the_finnish_feed_has_finnish_rights_text_and_the_english_feed_keeps_its_own():
    assert 'Fimea' in TEXT['fi']['rights'] and 'CC BY 4.0' in TEXT['fi']['rights'] and 'Data:' not in TEXT['fi']['rights'] and 'joined' not in TEXT['fi']['rights']
    assert TEXT['en']['rights'] == 'Data: Finnish Medicines Agency Fimea, CC BY 4.0. Selected, joined and transformed.'


def test_the_data_credit_says_impact_is_shortage_radars_reading():
    credit = fimea_credit({})
    assert 'impact' in credit and 'Shortage Radar' in credit and 'not a Fimea field' in credit
