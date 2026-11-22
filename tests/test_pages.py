import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pages import PAGES, SITE_URL, footer, header, render_pages

ROOT = Path(__file__).resolve().parents[1]
PAGE_FILES = ['index.html', 'shortages.html', 'medicine.html', 'trends.html', 'about.html']


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


def test_navigation_marks_the_current_page_and_lists_four_pages():
    out = render_pages(749)
    for key, meta in PAGES.items():
        nav = between(out[meta['file']], '<nav class="nav"', '</nav>')
        assert nav.count('<a ') == 4
        current = re.findall(r'<a href="([^"]+)" aria-current="page"', nav)
        assert current == ([meta['file']] if meta['nav'] else [])
    assert 'href="about.html#what-to-do"' in out['index.html']


def test_each_page_has_one_h1_a_skip_link_main_and_its_own_canonical_and_csp():
    out = render_pages(749)
    for f in PAGE_FILES:
        html = out[f]
        # The medicine page draws its h1 (the package name) when the data is loaded.
        assert html.count('<h1') == (0 if f == 'medicine.html' else 1), f
        assert 'class="skip-link" href="#main"' in html and '<main id="main"' in html
        assert 'name="referrer" content="no-referrer"' in html
        assert "default-src 'self'" in html and 'script-src \'self\'' in html and '<script>' not in html
        expected = SITE_URL + ('' if f == 'index.html' else f)
        assert f'<link rel="canonical" href="{expected}">' in html
        assert f'property="og:url" content="{expected}"' in html
        assert 'og:image:width" content="1200"' in html
    # Only the pages with a search form that sends the visitor elsewhere may submit forms.
    assert "form-action 'self'" in out['index.html'] and "form-action 'self'" in out['medicine.html']
    assert "form-action 'none'" in out['shortages.html'] and "form-action 'none'" in out['about.html']


def test_home_headline_carries_the_count_and_search_goes_to_the_list():
    html = render_pages(749)['index.html']
    assert 'Fimea lists 749 packages as short today.' in html
    assert 'data-count="749"' in html
    assert 'action="shortages.html" method="get"' in html and 'name="q"' in html
    assert 'Fimea lists 1 package as short today.' in render_pages(1)['index.html']


def test_404_page_uses_absolute_paths_for_the_project_site():
    html = render_pages(749)['404.html']
    assert 'href="/shortage-radar/style.css"' in html and 'src="/shortage-radar/lib.js"' in html
    assert 'href="/shortage-radar/shortages.html"' in html
    assert 'rel="canonical"' not in html


def test_sitemap_lists_the_four_indexable_pages():
    root = ET.parse(ROOT / 'site/sitemap.xml').getroot()
    urls = [e.text for e in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    assert urls == [SITE_URL, SITE_URL + 'shortages.html', SITE_URL + 'trends.html', SITE_URL + 'about.html']


def test_every_script_and_style_a_page_loads_exists():
    out = render_pages(749)
    for f in PAGE_FILES:
        for ref in re.findall(r'(?:src|href)="([^"/:#?]+\.(?:js|css|woff2|svg|png))"', out[f]):
            assert (ROOT / 'site' / ref).exists(), (f, ref)
