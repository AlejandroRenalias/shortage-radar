import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pages import PAGES, SITE_URL, footer, header, render_pages

ROOT = Path(__file__).resolve().parents[1]
PAGE_FILES = ['index.html', 'professionals.html', 'shortages.html', 'medicine.html', 'group.html', 'medicines.html', 'trends.html', 'about.html']


def between(html, start, end):
    return html[html.index(start):html.index(end) + len(end)]


def test_every_page_is_built_with_the_same_header_and_footer():
    out = render_pages(749)
    assert sorted(out) == sorted(PAGE_FILES + ['404.html'])
    headers = {between(out[f], '<header', '</header>') for f in PAGE_FILES}
    footers = {between(out[f], '<footer', '</footer>') for f in PAGE_FILES}
    # The header differs only in which link is the current page.
    normal = {re.sub(r' aria-current="page"|<i class="nav-mark" aria-hidden="true"></i>', '', h) for h in headers}
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
    assert 'href="about.html#what-to-do"' in out['professionals.html']


def test_each_page_has_one_h1_a_skip_link_main_and_its_own_canonical_and_csp():
    out = render_pages(749)
    for f in PAGE_FILES:
        html = out[f]
        # The medicine page draws its h1 (the package name) when the data is loaded.
        assert html.count('<h1') == (0 if f in ('medicine.html', 'group.html', 'medicines.html') else 1), f
        assert 'class="skip-link" href="#main"' in html and '<main id="main"' in html
        assert 'name="referrer" content="no-referrer"' in html
        assert "default-src 'self'" in html and 'script-src \'self\'' in html and '<script>' not in html
        expected = SITE_URL + ('' if f == 'index.html' else f)
        assert f'<link rel="canonical" href="{expected}">' in html
        assert f'property="og:url" content="{expected}"' in html
        assert 'og:image:width" content="1200"' in html
    # Only the pages with a search form that sends the visitor elsewhere may submit forms.
    assert "form-action 'self'" in out['professionals.html'] and "form-action 'self'" in out['medicine.html'] and "form-action 'self'" in out['medicines.html']
    assert "form-action 'none'" in out['shortages.html'] and "form-action 'none'" in out['about.html']


def test_home_headline_carries_the_count_and_search_goes_to_the_list():
    html = render_pages(749)['professionals.html']
    assert 'Fimea’s list: 749 packages in shortage now.' in html
    assert 'data-count="749"' in html
    assert 'action="shortages.html" method="get"' in html and 'name="q"' in html
    assert 'Fimea’s list: 1 package in shortage now.' in render_pages(1)['professionals.html']
    # Packages expected within two weeks are named apart from the ones short now.
    html = render_pages(714, soon=43)['professionals.html']
    assert '>Fimea’s list: 714 packages in shortage now, 43 more expected to start within 2 weeks.</h1>' in html and 'data-soon="43"' in html
    assert html.index('id="hero-label"') < html.index('id="hero-answer"')
    assert 'Our reading of Fimea’s register, not a stock check.' in html


def test_home_top_keeps_headline_strip_search_and_one_closed_dropdown_for_the_rest():
    html = render_pages(714, {'substitute': 539, 'no_alternative': 61, 'nogroup': 117, 'vet': 39}, None, 42)['professionals.html']
    top = html[:html.index('id="triage"')]
    # One dropdown at the top, closed, with the notes that used to stand open.
    assert top.count('<details') == 1 and '<details class="eu-fold eu-notes home-notes">' in top
    box = top[top.index('<details'):top.index('</details>')]
    assert 'data-i18n="homeNotes">How to read these numbers</summary>' in box
    assert 'including any that start after 2 weeks' in box
    for caveat in ('Our reading of Fimea’s register, not a stock check.', 'for 539, the check found another package',
                   'A listing does not tell you whether a medicine is available at your pharmacy.', 'Substitution groups are for human medicines.',
                   '“On the market” is not a pharmacy stock check.', 'Search by medicine, active substance, ATC, company or VNR.', 'href="about.html#impact"'):
        assert caveat in box, caveat
    # The old long lines are not outside the dropdown any more.
    outside = top.replace(box, '')
    for gone in ('id="hero-label"', 'id="hero-answer"', 'class="hint"', 'id="hero-sub"'):
        assert gone not in outside, gone
    assert html.count('home-notes') == 1  # the old notes box under the triage list is merged in
    # Date line is one paragraph with the file date and the check date.
    assert outside.count('id="hero-fresh"') == 1 and '<span id="hero-file"></span><span id="hero-checked"></span>' in outside


def test_404_page_uses_absolute_paths_for_the_project_site():
    html = render_pages(749)['404.html']
    assert 'href="/shortage-radar/style.css"' in html and 'src="/shortage-radar/lib.js"' in html
    assert 'href="/shortage-radar/shortages.html"' in html
    assert 'rel="canonical"' not in html


def test_sitemap_lists_the_indexable_pages():
    root = ET.parse(ROOT / 'site/sitemap.xml').getroot()
    urls = [e.text for e in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    assert urls == [SITE_URL, SITE_URL + 'shortages.html', SITE_URL + 'trends.html', SITE_URL + 'critical.html', SITE_URL + 'critical-methods.html', SITE_URL + 'professionals.html', SITE_URL + 'about.html']


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
    assert 'class="lang needs-js"' in out['professionals.html']
    # The home search is a plain form, so it still works without scripts.
    assert 'action="shortages.html" method="get"' in out['professionals.html'] and 'class="bigsearch"' in out['professionals.html']
    css = (ROOT / 'site/style.css').read_text(encoding='utf-8')
    assert 'html:not(.js) .needs-js{display:none}' in css and '[hidden]{display:none!important}' in css


def test_home_has_the_form_shelf_before_the_newest_cards_and_about_leads_with_the_answer():
    out = render_pages(749)
    home = out['professionals.html']
    assert home.index('id="shelf"') < home.index('id="newest"') < home.index('id="facts"')
    assert home.index('id="q"') < home.index('id="shelf"')
    about = out['about.html']
    assert about.index('data-i18n="aboutIntro"') < about.index('class="toc"') < about.index('id="what-to-do"')
    assert 'id="what-is"' not in about and about.count('<li><a href="#') == 11
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
    html = render_pages(749)['professionals.html']
    assert 'fonts/atkinson-latin.woff2' in html and 'fonts/public-sans-digits.woff2' in html


def test_tab_bar_markup_has_five_solid_icon_tabs_and_one_current_page():
    out = render_pages(749)
    nav = between(out['shortages.html'], '<nav class="nav"', '</nav>')
    tabs = re.findall(r'<a href="([^"]+)"( aria-current="page")?>(?:<i class="nav-mark" aria-hidden="true"></i>)?(<svg.*?</svg>)<span data-i18n="(\w+)">([^<]+)</span></a>', nav)
    assert [t[0] for t in tabs] == ['index.html', 'shortages.html', 'trends.html', 'critical.html', 'about.html']
    assert [t[3] for t in tabs] == ['navHome', 'navShortages', 'navTrends', 'navEuList', 'navAbout']
    assert [t[1] for t in tabs] == ['', ' aria-current="page"', '', '', '']
    for _, _, svg, _, _ in tabs:
        assert 'class="uicon ic-b"' in svg and 'aria-hidden="true"' in svg and 'focusable="false"' in svg
    assert 'aria-label="Main menu"' in nav


def test_finnish_shortages_tab_can_wrap_at_a_soft_hyphen():
    i18n = (ROOT / 'site' / 'i18n.js').read_text(encoding='utf-8')
    assert 'navShortages: "Saatavuus' + chr(92) + 'u00adhäiriöt"' in i18n
    assert i18n.count('navShortages:') == 2


def test_tab_bar_blends_in_clears_content_and_respects_motion_and_safe_area():
    css = (ROOT / 'site' / 'style.css').read_text(encoding='utf-8')
    nav = re.search(r'\n\.nav\{([^}]*)\}', css).group(1)
    assert 'position:fixed' in nav and 'left:0;right:0;bottom:0' in nav
    assert 'background:var(--surface)' in nav and 'border-top:1px solid var(--line)' in nav
    assert 'env(safe-area-inset-bottom)' in nav
    assert 'box-shadow' not in nav and 'border-radius' not in nav and 'var(--ink)' not in nav
    assert re.search(r'--nav-h:61px', css) and re.search(r'body\{[^}]*padding-bottom:calc\(var\(--nav-h\) \+ env\(safe-area-inset-bottom\)\)', css)
    assert re.search(r'\.nav a\{[^}]*min-height:var\(--nav-h\)', css)
    assert re.search(r'\.nav a\[aria-current="page"\]\{[^}]*color:var\(--green-ink\);font-weight:700', css)
    assert '.nav a:focus-visible{' in css
    assert re.search(r'@media \(min-width:720px\)\{\s*:root\{--nav-h:0px\}\s*body\{padding-bottom:0\}', css)
    assert re.search(r'prefers-reduced-motion:reduce\)\{\*,\*::before,\*::after\{animation:none!important', css)


def test_home_is_the_patient_page_and_the_old_home_is_the_professional_page():
    out = render_pages(749, {'substitute': 5, 'no_alternative': 1, 'nogroup': 1, 'vet': 1}, None, 3, '2026-11-24')
    home, pros = out['index.html'], out['professionals.html']
    assert 'data-page="index"' in home and 'src="patient.js"' in home and 'data-page="professionals"' in pros and 'src="home.js"' in pros
    # First screen: the question, the search and the hint, with the one closed dropdown after them; no counts, strip, picture or charts.
    main = home[home.index('<main'):home.index('</main>')]
    assert main.index('data-i18n="ptQuestion"') < main.index('role="search"') < main.index('data-i18n="ptHint"') < main.index('<details')
    assert main.count('<details') == 1 and '<details class="eu-fold eu-notes pt-info">' in main and '<details open' not in main
    for gone in ('class="strip"', 'id="triage"', 'eu-hero-art', 'id="hero-line"', 'id="facts"', 'id="shelf"'):
        assert gone not in main
    # The dropdown links to the professional page and the About page; the footer links to the professional page on every page.
    box = main[main.index('<details'):]
    assert 'href="professionals.html"' in box and 'href="about.html"' in box and 'data-i18n="ptInfoStock"' in box
    for html in out.values():
        assert 'href="professionals.html" data-i18n="footerPros"' in html or 'href="/shortage-radar/professionals.html" data-i18n="footerPros"' in html
    # The tab bar is unchanged: five tabs, no sixth, and the professional page is not one of them.
    for html in (home, pros):
        assert len(re.findall(r'<a href="[^"]+">?', between(html, '<nav class="nav"', '</nav>'))) == 5
        assert 'professionals.html' not in between(html, '<nav class="nav"', '</nav>')
    assert 'aria-current="page"' in between(home, '<nav class="nav"', '</nav>') and 'aria-current' not in between(pros, '<nav class="nav"', '</nav>')
    # The old home keeps its numbers.
    assert 'id="hero-line"' in pros and 'class="strip"' in pros and 'id="triage"' in pros


def test_patient_search_works_without_scripts_by_going_to_the_list():
    html = render_pages(749)['index.html']
    assert 'action="shortages.html" method="get"' in html and 'name="q"' in html


def test_tab_mark_is_one_element_in_the_current_tab_only():
    out = render_pages(749)
    for key, meta in PAGES.items():
        if meta.get('own') or not meta['nav']:
            continue
        nav = between(out[meta['file']], '<nav class="nav"', '</nav>')
        assert nav.count('class="nav-mark"') == 1
        assert re.search(r'aria-current="page"><i class="nav-mark" aria-hidden="true"></i><svg', nav)

def test_tab_mark_fades_in_by_css_only_below_720px_and_never_takes_pointer_input():
    css = (ROOT / 'site' / 'style.css').read_text(encoding='utf-8')
    block = re.search(r'@media \(max-width:719px\) and \(prefers-reduced-motion:no-preference\)\{(.*?)\n\}', css, re.S).group(1)
    # Entrance is inside the no-preference media query, so reduced motion gets none.
    assert '.nav a[aria-current="page"] .nav-mark{animation:tab-mark .2s ease-out both}' in block
    assert re.search(r'@keyframes tab-mark\{from\{opacity:0;transform:scale\(\.6\)\}to\{opacity:1;transform:none\}\}', css)
    assert css.count('tab-mark') == 2 and 'animation:tab-mark' not in css.replace(block, '')
    assert re.search(r'\.nav-mark\{pointer-events:none;', css)
    # The entrance waits while the page is hidden for i18n, and plays once the class is removed; without JavaScript the class never exists.
    assert 'html.i18n-pending .nav a[aria-current="page"] .nav-mark{animation:none}' in block
    assert block.index('animation:tab-mark') < block.index('html.i18n-pending')
    assert 'html.i18n-pending body{' in css
    assert re.search(r'@media \(min-width:720px\)\{[^@]*\.nav-mark\{display:none\}', css, re.S)


def test_no_page_script_or_stored_state_for_the_tab_mark():
    css = (ROOT / 'site' / 'style.css').read_text(encoding='utf-8')
    assert 'view-transition' not in css and '--sr-steps' not in css and 'sr-slide' not in css
    assert not (ROOT / 'site' / 'tabbar.js').exists()
    out = render_pages(749)
    for meta in PAGES.values():
        if meta['file'] not in out:
            continue
        assert 'tabbar.js' not in out[meta['file']] and 'referrerpolicy' not in out[meta['file']]
