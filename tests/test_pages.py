import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pages import PAGES, SITE_URL, footer, header, render_pages

ROOT = Path(__file__).resolve().parents[1]
PAGE_FILES = ['index.html', 'shortages.html', 'medicine.html', 'medicines.html', 'trends.html', 'about.html']


def between(html, start, end):
    return html[html.index(start):html.index(end) + len(end)]


def test_every_page_is_built_with_the_same_header_and_footer():
    out = render_pages(749)
    assert sorted(out) == sorted(PAGE_FILES + ['404.html'])
    headers = {between(out[f], '<header', '</header>') for f in PAGE_FILES}
    footers = {between(out[f], '<footer', '</footer>') for f in PAGE_FILES}
    # The header differs only in which link is the current page.
    normal = {re.sub(r' aria-current="page"', '', h) for h in headers}
    assert len(normal) == 1 and len(footers) == 1
    for f in PAGE_FILES:
        assert between(out[f], '<header', '</header>') == header(re.search(r'data-page="(\w+)"', out[f]).group(1), '').split('\n')[0]
        assert out[f].count('<footer') == 1 and out[f].count('data-lang-btn="fi"') == 1


def test_navigation_marks_the_current_page_and_lists_five_pages():
    out = render_pages(749)
    for key, meta in PAGES.items():
        if meta.get('own'):
            continue
        nav = between(out[meta['file']], '<nav class="nav"', '</nav>')
        assert nav.count('<a ') == 5
        current = re.findall(r'<a href="([^"]+)" aria-current="page"', nav)
        assert current == ([meta['file']] if meta['nav'] else [])
    assert 'href="about.html#what-to-do"' in out['index.html']


def test_each_page_has_one_h1_a_skip_link_main_and_its_own_canonical_and_csp():
    out = render_pages(749)
    for f in PAGE_FILES:
        html = out[f]
        # The medicine page draws its h1 (the package name) when the data is loaded.
        assert html.count('<h1') == (0 if f in ('medicine.html', 'medicines.html') else 1), f
        assert 'class="skip-link" href="#main"' in html and '<main id="main"' in html
        assert 'name="referrer" content="no-referrer"' in html
        assert "default-src 'self'" in html and 'script-src \'self\'' in html and '<script>' not in html
        expected = SITE_URL + ('' if f == 'index.html' else f)
        assert f'<link rel="canonical" href="{expected}">' in html
        assert f'property="og:url" content="{expected}"' in html
        assert 'og:image:width" content="1200"' in html
    # Only the pages with a search form that sends the visitor elsewhere may submit forms.
    assert "form-action 'self'" in out['index.html'] and "form-action 'self'" in out['medicine.html'] and "form-action 'self'" in out['medicines.html']
    assert "form-action 'none'" in out['shortages.html'] and "form-action 'none'" in out['about.html']


def test_home_headline_carries_the_count_and_search_goes_to_the_list():
    html = render_pages(749)['index.html']
    assert 'Fimea: 749 short now.' in html
    assert 'data-count="749"' in html
    assert 'action="shortages.html" method="get"' in html and 'name="q"' in html
    assert 'Fimea: 1 short now.' in render_pages(1)['index.html']
    # Packages expected within two weeks are named apart from the ones short now.
    html = render_pages(714, soon=43)['index.html']
    assert '>Fimea: 714 short now, 43 more expected within 2 weeks.</h1>' in html and 'data-soon="43"' in html
    assert html.index('id="hero-label"') < html.index('id="hero-answer"')
    assert 'Our reading of Fimea’s register, not a stock check.' in html


def test_404_page_uses_absolute_paths_for_the_project_site():
    html = render_pages(749)['404.html']
    assert 'href="/shortage-radar/style.css"' in html and 'src="/shortage-radar/lib.js"' in html
    assert 'href="/shortage-radar/shortages.html"' in html
    assert 'rel="canonical"' not in html


def test_sitemap_lists_the_indexable_pages():
    root = ET.parse(ROOT / 'site/sitemap.xml').getroot()
    urls = [e.text for e in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    assert urls == [SITE_URL, SITE_URL + 'shortages.html', SITE_URL + 'trends.html', SITE_URL + 'critical.html', SITE_URL + 'critical-methods.html', SITE_URL + 'about.html']


def test_every_script_and_style_a_page_loads_exists():
    out = render_pages(749)
    for f in PAGE_FILES:
        for ref in re.findall(r'(?:src|href)="([^"/:#?]+\.(?:js|css|woff2|svg|png))"', out[f]):
            assert (ROOT / 'site' / ref).exists(), (f, ref)


def test_without_scripts_dead_controls_are_hidden_and_the_data_files_are_linked():
    out = render_pages(749)
    for f in ['shortages.html', 'medicine.html', 'medicines.html', 'trends.html']:
        html = out[f]
        assert 'needs-js' in html
        noscript = between(html, '<noscript>', '</noscript>')
        assert 'shortages.csv' in noscript and 'data.json' in noscript and 'fimea.fi' in noscript
    assert 'class="wrap finder needs-js"' in out['shortages.html'] and 'class="wrap results needs-js"' in out['shortages.html']
    assert 'class="wrap needs-js" id="medicine"' in out['medicine.html'] and 'class="wrap needs-js" id="medicines"' in out['medicines.html']
    assert 'class="lang needs-js"' in out['index.html']
    # The home search is a plain form, so it still works without scripts.
    assert 'action="shortages.html" method="get"' in out['index.html'] and 'class="bigsearch"' in out['index.html']
    css = (ROOT / 'site/style.css').read_text(encoding='utf-8')
    assert 'html:not(.js) .needs-js{display:none}' in css and '[hidden]{display:none!important}' in css


def test_home_has_the_form_shelf_before_the_newest_cards_and_about_leads_with_the_answer():
    out = render_pages(749)
    home = out['index.html']
    assert home.index('id="shelf"') < home.index('id="newest"') < home.index('id="facts"')
    assert home.index('id="q"') < home.index('id="shelf"')
    about = out['about.html']
    assert about.index('data-i18n="aboutIntro"') < about.index('class="toc"') < about.index('id="what-to-do"')
    assert 'id="what-is"' not in about and about.count('<li><a href="#') == 10
    assert about.index('id="substitution"') < about.index('id="impact"') < about.index('id="how"')


def test_pages_load_only_small_data_files():
    root = ROOT / 'site'
    for name in ['home.js', 'trends.js', 'about.js']:
        text = (root / name).read_text(encoding='utf-8')
        assert 'data.json' not in text and 'current.json' not in text, name
    assert 'data.json' not in (root / 'medicine.js').read_text(encoding='utf-8')
    assert "p/${vnr.slice(-2)}.json" in (root / 'medicine.js').read_text(encoding='utf-8')


def test_every_face_of_the_site_font_family_declares_the_same_weight_range():
    """Faces of one family with different font-weight ranges are not combined by unicode-range:
    the browser picks one of them for a weight, and every character it does not cover falls back to Arial.
    The digits face once had 100 900 against the letters' 200 800, and all letters rendered in Arial."""
    css = (ROOT / 'site/style.css').read_text(encoding='utf-8')
    faces = re.findall(r"@font-face\{font-family:'Atkinson Hyperlegible Next';([^}]*)\}", css)
    assert len(faces) == 3
    assert {re.search(r'font-weight:([\d ]+);', f).group(1) for f in faces} == {'200 800'}
    ranges = [re.search(r'unicode-range:([^;}]+)', f).group(1) for f in faces]
    assert any(r == 'U+0030-0039' for r in ranges)
    html = render_pages(749)['index.html']
    assert 'fonts/atkinson-latin.woff2' in html and 'fonts/public-sans-digits.woff2' in html
