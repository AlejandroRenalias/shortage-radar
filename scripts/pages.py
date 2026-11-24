"""Static pages for the site: one shared header and footer, five page bodies and the 404 page.

The English text here is the no-script text. site/i18n.js holds the same text for English and Finnish,
and tests/test_pages.py checks that the two agree, so a string is only ever changed in one idea.
"""
from html import escape

from critical_charts import hero_art

SITE_URL = 'https://alejandrorenalias.github.io/shortage-radar/'
PREVIEW = SITE_URL + 'preview.png'
PREVIEW_ALT = 'Shortage Radar / Saatavuustutka: medicine shortages in Finland'
ARCHIVE_NOTE = 'Daily archive since 21 Nov 2026, with earlier captures from the Internet Archive.'

PAGES = {
    'index': {'file': 'index.html', 'nav': 'navHome', 'icon': 'home', 'title': 'Shortage Radar: medicine shortages in Finland',
              'description': 'Is your medicine short in Finland? Search Fimea’s list of reported medicine shortages and see since when and until when.', 'form_action': "'self'"},
    'shortages': {'file': 'shortages.html', 'nav': 'navShortages', 'icon': 'list', 'title': 'Medicine shortages in Finland | Shortage Radar',
                  'description': 'Search and filter every medicine package that Fimea lists as short in Finland, with start dates and the company’s estimated end dates.', 'form_action': "'none'"},
    'trends': {'file': 'trends.html', 'nav': 'navTrends', 'icon': 'chart', 'title': 'Shortage trends in Finland | Shortage Radar',
               'description': 'How many medicine shortages Finland has had over time, what changed this week, and which medicine groups are most affected.', 'form_action': "'none'"},
    'critical': {'file': 'critical.html', 'nav': 'navEuList', 'icon': 'shield', 'own': True, 'title': 'Critical medicines in Finland | Shortage Radar',
                 'description': 'Medicines on the EU Union list of critical medicines that Fimea lists as short in Finland.', 'form_action': "'none'"},
    'about': {'file': 'about.html', 'nav': 'navAbout', 'icon': 'info', 'title': 'About the data | Shortage Radar',
              'description': 'What a medicine shortage is, what to do about one, and how this site gets and uses Fimea’s open data.', 'form_action': "'none'"},
    'medicine': {'file': 'medicine.html', 'nav': None, 'icon': None, 'title': 'Medicine | Shortage Radar',
                 'description': 'One medicine package on Fimea’s shortage list: status, timeline and what to do.', 'form_action': "'self'"},
    'medicines': {'file': 'medicines.html', 'nav': None, 'icon': None, 'title': 'Medicine and its packages | Shortage Radar',
                  'description': 'One medicine on Fimea’s shortage list, with the notices and history of each package.', 'form_action': "'self'"},
}
NAV_LABELS = {'navHome': 'Home', 'navShortages': 'Shortages', 'navEuList': 'EU list', 'navTrends': 'Trends', 'navAbout': 'About'}
NAV_ICONS = {
    'home': '<path d="M3.500 11 12 4l8.500 7M6 9.500V20h12V9.500"/>',
    'list': '<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
    'chart': '<path d="M4 20V4M4 20h16M8 15l3-4 3 2 5-7"/>',
    'shield': '<path d="M12 3.500 5 6.500v5c0 4.500 3 7.500 7 9 4-1.500 7-4.500 7-9v-5z"/><path d="M12 9v6M9 12h6"/>',
    'info': '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.500h.01"/>',
}
MARK = '<svg class="mark" viewBox="0 0 32 32" width="32" height="32" aria-hidden="true" focusable="false"><rect width="32" height="32" rx="9" fill="#00875a"/><path d="M16 8v16M8 16h16" stroke="#fff" stroke-width="3.500" stroke-linecap="round"/></svg>'


def icon(name):
    return f'<svg class="uicon" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false">{NAV_ICONS[name]}</svg>'


def head(page, prefix, meta):
    url = SITE_URL + ('' if page == 'index' else meta['file'])
    csp = f"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action {meta['form_action']}"
    title, desc = escape(meta['title'], quote=True), escape(meta['description'], quote=True)
    scripts = f'<script src="{prefix}language.js"></script><script src="{prefix}i18n.js" defer></script><script src="{prefix}lib.js" defer></script>'
    if meta.get('script'):
        scripts += f'<script src="{prefix}{meta["script"]}" defer></script>'
    canonical = f'<link rel="canonical" href="{url}">' if page != '404' else ''
    og = (f'<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:type" content="website"><meta property="og:url" content="{url}">'
          f'<meta property="og:image" content="{PREVIEW}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{PREVIEW_ALT}">'
          '<meta property="og:locale" content="en_GB"><meta property="og:locale:alternate" content="fi_FI">'
          f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{desc}"><meta name="twitter:image" content="{PREVIEW}"><meta name="twitter:image:alt" content="{PREVIEW_ALT}">') if page != '404' else ''
    return (f'<head>\n<meta charset="utf-8">\n<meta http-equiv="Content-Security-Policy" content="{csp}">\n<meta name="referrer" content="no-referrer">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n<meta name="description" content="{desc}">\n<meta name="theme-color" content="#fbfdfc">\n{canonical}\n{og}\n'
            f'<link rel="alternate" type="application/atom+xml" title="Shortage Radar: changes (English)" href="{prefix}feed.xml"><link rel="alternate" type="application/atom+xml" title="Saatavuustutka: muutokset (suomi)" href="{prefix}feed-fi.xml">\n'
            f'<link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml"><link rel="icon" href="{prefix}favicon-32.png" sizes="32x32"><link rel="apple-touch-icon" href="{prefix}apple-touch-icon.png">\n'
            f'<link rel="preload" href="{prefix}fonts/atkinson-latin.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="{prefix}fonts/public-sans-digits.woff2" as="font" type="font/woff2" crossorigin>\n'
            f'<title>{escape(meta["title"])}</title><link rel="stylesheet" href="{prefix}style.css">{scripts}</head>')


def header(current, prefix):
    links = []
    for key, meta in PAGES.items():
        if not meta['nav']:
            continue
        mark = ' aria-current="page"' if key == current else ''
        links.append(f'<a href="{prefix}{meta["file"]}"{mark}>{icon(meta["icon"])}<span data-i18n="{meta["nav"]}">{NAV_LABELS[meta["nav"]]}</span></a>')
    return ('<header class="site-header"><div class="wrap header-bar">'
            f'<a class="brand" href="{prefix}index.html">{MARK}<span data-i18n="brand">Shortage Radar</span></a>'
            f'<nav class="nav" aria-label="Main menu" data-i18n-attr="aria-label=navLabel">{"".join(links)}</nav>'
            '<div class="lang needs-js" role="group" aria-label="Language" data-i18n-attr="aria-label=languageLabel"><button type="button" lang="fi" data-lang-btn="fi" aria-pressed="false">Suomi</button><button type="button" lang="en" data-lang-btn="en" aria-pressed="false">English</button></div>'
            '</div></header>\n'
            '<div class="stale" id="stale" hidden><div class="wrap"><svg class="uicon" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path d="M12 3.500 2.500 20h19z"/><path d="M12 10v4.500M12 17.500h.01"/></svg><p id="stale-text"></p></div></div>')


def footer(prefix):
    pages = ''.join(f'<li><a href="{prefix}{m["file"]}" data-i18n="{m["nav"]}">{NAV_LABELS[m["nav"]]}</a></li>' for m in PAGES.values() if m['nav'])
    return ('<footer class="site-footer"><div class="wrap foot"><div class="foot-about">'
            f'<p class="foot-brand">{MARK}<span data-i18n="brand">Shortage Radar</span></p>'
            '<p data-i18n="footerTag">Reported medicine shortages in Finland, from Fimea open data. Not medical advice.</p>'
            '<p><span data-i18n="footerAgency">Finnish Medicines Agency Fimea</span>, <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. <span data-i18n="footerTransform">Data was selected, joined and transformed.</span></p>'
            '<p data-i18n="footerEma">EU list of critical medicines: European Medicines Agency (EMA).</p>'
            f'<p class="foot-feedback"><a href="{prefix}about.html#feedback" data-i18n="footerFeedback">About and feedback</a></p>'
            '<p><span data-i18n="archiveCredit">Earlier captures:</span> <a href="https://web.archive.org/">Internet Archive (web.archive.org)</a></p>'
            '<p id="source-times" class="foot-times"></p><p class="foot-times" data-i18n="footerNote">Source times show when the files were last modified; the publisher does not provide release times.</p></div>'
            f'<div><h2 class="foot-title" data-i18n="footerPages">Pages</h2><ul>{pages}</ul></div>'
            f'<div><h2 class="foot-title" data-i18n="footerData">Data</h2><ul><li><a href="{prefix}shortages.csv" data-i18n="footerCsv">Table (CSV)</a></li><li><a href="{prefix}data.json" data-i18n="footerJson">Full data (JSON)</a></li>'
            f'<li><a href="{prefix}feed.xml" data-feed data-i18n="footerFeed">Changes (feed)</a></li><li><a href="https://fimea.fi/en/about_us/open-data" data-fimea="data" data-i18n="sourceLink">Source and licence</a></li></ul></div>'
            '</div></footer>')


def document(page, body, prefix='', meta=None):
    meta = meta or PAGES[page]
    skip = f'<a class="skip-link" href="#main" data-i18n="skip">Skip to content</a>'
    noscript = f'<noscript><p class="noscript">JavaScript is needed to show the shortage data. / Saatavuustietojen näyttäminen edellyttää JavaScriptiä. <a href="{prefix}shortages.csv">CSV</a>, <a href="{prefix}data.json">JSON</a>, <a href="https://fimea.fi/en/about_us/open-data">Fimea</a></p></noscript>'
    return (f'<!doctype html>\n<html lang="en" data-page="{page}">\n{head(page, prefix, meta)}\n<body>\n{skip}\n{header(page, prefix)}\n{noscript}\n'
            f'<main id="main" tabindex="-1">\n{body}\n</main>\n{footer(prefix)}\n</body></html>\n')


def load_error(extra=''):
    return f'<p class="state" id="load-error" hidden>Data could not be loaded. Try again later. / Tietoja ei voitu ladata. Yritä myöhemmin uudelleen. <a href="https://fimea.fi/en/about_us/open-data">Fimea</a></p>{extra}'


def search_icon():
    return '<svg class="uicon" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="7"/><path d="m16.500 16.500 4 4"/></svg>'


IMPACT_ICONS = {
    'substitute': '<path d="M4 8h14l-3.500-3.500M20 16H6l3.500 3.500"/>',
    'critical': '<path d="M5 4.500h14a1.500 1.500 0 0 1 1.500 1.500v9a1.500 1.500 0 0 1-1.500 1.500h-7.500L7 20v-3.500H5A1.500 1.500 0 0 1 3.500 15V6A1.500 1.500 0 0 1 5 4.500z"/><path d="M8 9h8M8 12.500h5"/>',
    'nogroup': '<rect x="4" y="4" width="16" height="16" rx="4"/><path d="M8.500 12h7"/>',
}
IMPACT_ICONS['no_alternative'] = IMPACT_ICONS['critical']  # the About page still names its icon 'critical'
IMPACT_NAMES = {'substitute': 'Substitute usually available', 'no_alternative': 'No interchangeable product on the market', 'nogroup': 'No substitution group'}
IMPACT_NOTES = {'substitute': 'Other packages in the same substitution group are on the market.', 'no_alternative': 'Talk to your pharmacist or doctor early.',
                'nogroup': 'Often hospital medicines or medicines from one company. Ask your pharmacist.'}


def triage_bar(share):
    """One level's share of the human packages, as a bar. The number beside it says the same in words."""
    return (f'<svg class="tri-bar" viewBox="0 0 100 6" preserveAspectRatio="none" aria-hidden="true" focusable="false"><rect class="track" width="100" height="6"/>'
            f'<rect class="part" width="{share:.2f}" height="6"/></svg>')


def triage_list(impact):
    total = sum(impact.get(k, 0) for k in IMPACT_NAMES) or 1
    rows = []
    for key, name in IMPACT_NAMES.items():
        n = impact.get(key, 0)
        rows.append(f'<li><a class="tri tri-{key}" href="shortages.html?impact={key}"><svg class="uicon" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">{IMPACT_ICONS[key]}</svg>'
                    f'<span class="tri-num">{n:,}</span><span class="tri-text"><strong data-i18n="impact_{key}">{name}</strong><span data-i18n="triageNote_{key}">{IMPACT_NOTES[key]}</span></span>'
                    '<svg class="uicon tri-go" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path d="m9 6 6 6-6 6"/></svg>'
                    f'{triage_bar(100 * n / total)}</a></li>')
    return ''.join(rows)


def home(count, impact=None, soon=0):
    """`count` packages are short now, and `soon` more are expected within two weeks."""
    line = f'Fimea: {count:,} short now{f", {soon:,} more expected within 2 weeks" if soon else ""}.'
    impact = impact or {}
    sub, vet = impact.get('substitute', 0), impact.get('vet', 0)
    answer = f'<p class="hero-answer" id="hero-answer" data-count="{sub}">For {sub:,} of them, the register lists an interchangeable package that is on the market and not flagged short.</p>' if impact else '<p class="hero-answer" id="hero-answer"></p>'
    vet_line = f'Also on the list: {vet:,} veterinary {"medicine" if vet == 1 else "medicines"}.'
    return f'''<section class="hero wrap"><div class="hero-grid"><div class="hero-head"><div class="hero-text">
<h1 id="hero-line" data-count="{count}" data-soon="{soon}">{line}</h1>
<p class="hero-fresh" id="hero-fresh" hidden><span id="hero-file"></span><span id="hero-checked"></span></p>
<p class="hero-label" id="hero-label" data-i18n="heroReading">Our reading of Fimea’s register, not a stock check.</p>
{answer}
<form class="bigsearch" action="shortages.html" method="get" role="search">
<label for="q" data-i18n="homeSearchLabel">Search for your medicine</label>
<div class="searchrow">{search_icon()}<input id="q" name="q" type="search" autocomplete="off" maxlength="100" placeholder="e.g. Burana or ibuprofen" data-i18n-attr="placeholder=placeholder"><button type="submit" class="btn" data-i18n="searchButton">Search</button></div>
<p class="hint" data-i18n="hint">Search by medicine, active substance, ATC, company or VNR.</p>
</form>
</div>{hero_art()}</div>
<section class="triage" id="triage" aria-labelledby="triage-title" data-impact="{escape(','.join(f'{k}:{impact.get(k, 0)}' for k in ('substitute', 'no_alternative', 'nogroup', 'vet')), quote=True)}"><h2 id="triage-title" data-i18n="impactQuestion">Can the pharmacy give a substitute?</h2>
<ul class="triage-list" id="triage-list">{triage_list(impact)}</ul>
<p class="triage-vet"><a href="shortages.html?impact=vet" id="triage-vet">{vet_line}</a></p>
<details class="eu-fold eu-notes home-notes"><summary data-i18n="homeNotes">Notes: what these numbers mean</summary>
<p id="hero-sub" data-i18n="heroSub">Includes shortages that have started and ones expected within two weeks. A listing does not tell you whether a medicine is available at your pharmacy.</p>
<p data-i18n="triageVetNote">Substitution groups are for human medicines.</p>
<p class="note"><span data-i18n="triageHint">Counts are packages. “On the market” is not a pharmacy stock check.</span> <a href="about.html#impact" data-i18n="impactLink">What the impact label means</a></p></details>
</section></div></section>
<section class="wrap home-section needs-js" aria-labelledby="shelf-title"><h2 id="shelf-title" data-i18n="shelfTitle">Browse by form</h2><p class="note" data-i18n="shelfIntro">Pick a form to see its shortages.</p><ul class="shelf-grid" id="shelf"></ul></section>
<section class="wrap home-section newest needs-js" aria-labelledby="newest-title"><h2 id="newest-title" data-i18n="heroNewest">Newest on the list</h2><div id="newest" class="rail"></div></section>
<section class="wrap home-section facts-block needs-js" aria-labelledby="facts-title">
<div class="facts-head"><h2 id="facts-title">This week</h2><p id="facts-since"></p></div>
<dl class="facts" id="facts"></dl>
</section>
<section class="wrap paths" aria-labelledby="paths-title">
<h2 id="paths-title" class="sr-only" data-i18n="pathsTitle">Where to next</h2>
<a class="path" href="shortages.html"><svg class="uicon" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="7"/><path d="m16.500 16.500 4 4"/></svg><span><strong data-i18n="pathFind">Find a medicine</strong><span data-i18n="pathFindText">Search the full list and filter it by group, form and company.</span></span></a>
<a class="path" href="trends.html"><svg class="uicon" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" focusable="false"><path d="M4 20V4M4 20h16M8 15l3-4 3 2 5-7"/></svg><span><strong data-i18n="pathTrends">See trends</strong><span data-i18n="pathTrendsText">How many shortages there are and how that has changed.</span></span></a>
<a class="path" href="about.html#what-to-do"><svg class="uicon" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" focusable="false"><path d="M12 4v16M4 12h16"/><rect x="3" y="3" width="18" height="18" rx="5"/></svg><span><strong data-i18n="pathAdvice">What to do if your medicine is short</strong><span data-i18n="pathAdviceText">Short steps for patients and relatives.</span></span></a>
</section>
{load_error()}'''


def shortages():
    return f'''<div class="wrap page-head"><h1 data-i18n="listTitle">Medicine shortages</h1><p class="lead" data-i18n="listIntro">Every package Fimea lists as short or soon to be short. Open a package to see its timeline.</p></div>
<div class="wrap finder needs-js">
<form id="finder" role="search" novalidate>
<label class="sr-only" for="search" data-i18n="searchLabel">Search shortages</label>
<div class="searchrow">{search_icon()}<input id="search" type="search" autocomplete="off" maxlength="100" placeholder="e.g. Burana or ibuprofen" data-i18n-attr="placeholder=placeholder"></div>
<p class="hint" id="search-hint" data-i18n="hint">Search by medicine, active substance, ATC, company or VNR.</p>
<details class="filters" id="filters"><summary><span data-i18n="filters">Filters</span><span id="filters-count"></span></summary>
<div class="filter-grid">
<fieldset class="seg seg-impact"><legend data-i18n="impactFilter">Impact</legend>
<label><input type="radio" name="impact" value="" checked><span data-i18n="impactAll">All</span></label>
<label><input type="radio" name="impact" value="no_alternative"><span data-i18n="impact_no_alternative">No interchangeable product on the market</span></label>
<label><input type="radio" name="impact" value="substitute"><span data-i18n="impact_substitute">Substitute usually available</span></label>
<label><input type="radio" name="impact" value="nogroup"><span data-i18n="impact_nogroup">No substitution group</span></label>
<label><input type="radio" name="impact" value="vet"><span data-i18n="impact_vet">Veterinary medicines</span></label></fieldset>
<fieldset class="seg"><legend data-i18n="filterStatus">Status</legend>
<label><input type="radio" name="status" value="" checked><span data-i18n="statusAll">All</span></label>
<label><input type="radio" name="status" value="now"><span data-i18n="statusNow">Shortage now</span></label>
<label><input type="radio" name="status" value="soon"><span data-i18n="statusSoon">Starting soon</span></label></fieldset>
<div class="field"><label for="f-group" data-i18n="filterGroup">Medicine group</label><select id="f-group"></select></div>
<div class="field"><label for="f-form" data-i18n="filterForm">Form</label><select id="f-form"></select></div>
<div class="field"><label for="f-company" data-i18n="filterCompany">Company</label><select id="f-company"></select></div>
<div class="field"><label for="sort" data-i18n="sortLabel">Sort by</label><select id="sort"><option value="" data-i18n="sortDefault">Current first</option><option value="name" data-i18n="sortName">Name</option><option value="longest" data-i18n="sortLongest">Earliest reported start</option><option value="end" data-i18n="sortEnd">Expected back soonest</option></select></div>
<button type="button" class="btn-quiet" id="clear" data-i18n="clearFilters" hidden>Clear filters</button>
</div></details>
</form>
</div>
<div class="wrap results needs-js">
<p class="crit-callout" id="crit-callout" hidden><svg class="uicon" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">{IMPACT_ICONS['no_alternative']}</svg><span id="crit-callout-text"></span> <a href="shortages.html?impact=no_alternative" id="crit-show" data-i18n="critShow">Show them by medicine</a></p>
<p class="crit-intro" id="crit-intro" data-i18n="critIntro" hidden>One row for each medicine and form. Open a row to see its packages. Talk to your pharmacist or doctor early about these medicines.</p>
<div class="list-meta"><p id="result-count" aria-live="polite" aria-atomic="true"></p><button type="button" class="btn-quiet" id="copy-link" data-i18n="copyLink">Copy search link</button><span id="copy-status" role="status"></span></div>
<div id="list" class="pkg-list"><p class="state" id="loading">Loading…</p></div>
<div class="more"><p id="more-count"></p><button type="button" class="btn" id="more" data-i18n="more" hidden>Show more</button></div>
{load_error()}
</div>'''


def medicine():
    return f'''<div class="wrap needs-js" id="medicine"><p class="state" id="loading">Loading…</p></div>
<div class="wrap">{load_error()}</div>'''


def medicines():
    return f'''<div class="wrap needs-js" id="medicines"><p class="state" id="loading">Loading…</p></div>
<div class="wrap">{load_error()}</div>'''


def trends():
    return f'''<div class="wrap page-head"><h1 data-i18n="trendsTitle">Trends</h1><p class="lead" data-i18n="trendsIntro">How many packages Fimea lists as short, and how that has changed.</p><p class="data-date needs-js" id="data-date"></p></div>
<div class="wrap trend-grid needs-js">
<section class="panel panel-wide" aria-labelledby="chart-title"><h2 id="chart-title" data-i18n="chartTitle">Packages on the list over time</h2><p id="history-note" class="note"></p><div id="chart" class="chart"></div><p id="rss-note" class="note"></p>
<details class="data-table"><summary data-i18n="tableToggle">Show the chart data as a table</summary><div id="chart-table"></div></details></section>
<section class="panel" id="week" aria-labelledby="week-title"><h2 id="week-title" data-i18n="weekTitle">This week</h2><p id="week-window" class="note"></p><dl class="mini-facts" id="week-facts"></dl><p><a id="feed-link" href="feed.xml" data-feed data-i18n="feedLink">Follow changes (feed)</a></p></section>
<section class="panel" aria-labelledby="longest-title"><h2 id="longest-title" data-i18n="longestTitle">Earliest reported starts</h2><p class="note" data-i18n="longestNote">Current shortages ranked by the start date the company reported. Days since that date are not days observed on the list: the archive has gaps.</p><ol id="longest-list" class="longest"></ol></section>
<section class="panel" aria-labelledby="group-title"><h2 id="group-title" data-i18n="byGroup">By medicine group</h2><p class="note" data-i18n="byGroupNote">Packages on the list, by medicine group.</p><div id="atc"></div></section>
<section class="panel panel-wide" id="new-crit" aria-labelledby="new-crit-title"><h2 id="new-crit-title" data-i18n="newCritTitle">Newly without an interchangeable product</h2><p class="note" data-i18n="newCritIntro">Days when the last available package of a substitution group went short, so no interchangeable product was left on the market.</p><ol id="new-crit-list" class="crit-events"></ol><p id="new-crit-method" class="note"></p><div id="triage-record"></div><p><a href="about.html#impact" data-i18n="impactLink">What the impact label means</a></p></section>
<section class="panel panel-wide" id="end-changes" aria-labelledby="end-changes-title"><h2 id="end-changes-title" data-i18n="endChangesTitle">End dates that changed</h2><p id="end-changes-text" class="big-note"></p><p id="end-changes-note" class="note"></p></section>
<section class="panel panel-wide cite" id="cite-box" aria-labelledby="cite-title" hidden><h2 id="cite-title" data-i18n="citeTitle">Cite this site</h2><p class="note" data-i18n="citeIntro">Use the data date and the source when you cite these figures.</p><p id="citation" class="citation"></p><button type="button" class="btn" id="copy-cite" data-i18n="copyCite">Copy citation</button> <span id="copy-status" role="status"></span></section>
</div>
<div class="wrap">{load_error()}</div>'''


def about():
    return f'''<div class="wrap page-head"><h1 data-i18n="aboutH1">About the data</h1><p class="lead" data-i18n="aboutIntro">The company has told Fimea it cannot deliver this package for a while. Your pharmacy may still have some. Ask your pharmacy what is available.</p></div>
<div class="wrap about-layout">
<nav class="toc" aria-labelledby="toc-title"><p id="toc-title" class="toc-title" data-i18n="aboutToc">On this page</p><ul>
<li><a href="#about-site" data-i18n="aboutShortTitle">About Shortage Radar</a></li><li><a href="#what-to-do" data-i18n="pathAdvice">What to do if your medicine is short</a></li><li><a href="#substitution" data-i18n="substTitle">Substitution groups</a></li><li><a href="#impact" data-i18n="impactTitle">What the impact label means</a></li><li><a href="#how" data-i18n="howTitle2">How the data works</a></li><li><a href="#limits" data-i18n="limitsTitle">What the data cannot tell you</a></li><li><a href="#downloads" data-i18n="downloadsTitle">Downloads</a></li><li><a href="#cite" data-i18n="citeTitle">Cite this site</a></li><li><a href="#privacy" data-i18n="privacyTitle">Privacy</a></li><li><a href="#licence" data-i18n="licenceTitle">Licence</a></li><li><a href="#feedback" data-i18n="feedbackTitle">Feedback</a></li></ul></nav>
<div class="prose">
<section id="about-site" aria-labelledby="h-about-site"><h2 id="h-about-site" data-i18n="aboutShortTitle">About Shortage Radar</h2><p data-i18n="aboutPurpose">Shortage Radar shows the medicine shortages that companies report in Finland. It makes Fimea’s open list easy to search and read.</p><p data-i18n="aboutIndep">It is an independent open-source project. Fimea and EMA do not run it and do not endorse it.</p>
<h3 data-i18n="aboutNotTitle">Three things to keep in mind</h3>
<ul class="steps"><li data-i18n="aboutNot1">A reported shortage does not mean the medicine is unavailable everywhere. A pharmacy may still have it.</li><li data-i18n="aboutNot2">A package that is not on the list is not necessarily available. The list shows reports only. It does not show stock.</li><li data-i18n="aboutNot3">A listed alternative is information, not medical advice. Ask a pharmacist or doctor before you change a medicine.</li></ul>
<details class="fold"><summary data-i18n="aboutSrcTitle">Sources and licences</summary><div><p><span data-i18n="aboutSrcFimea">Shortages: Finnish Medicines Agency Fimea, open data, licensed CC BY 4.0.</span> <a href="https://fimea.fi/en/about_us/open-data" data-fimea="data" data-i18n="aboutSrcFimeaLink">Fimea open data and licence</a></p>
<p><span data-i18n="aboutSrcEma">EU list of critical medicines: European Medicines Agency (EMA) and the Heads of Medicines Agencies. EMA is the source of the list.</span> <a href="https://www.ema.europa.eu/en/human-regulatory-overview/post-authorisation/medicine-shortages-availability-issues/availability-medicines-during-crises/union-list-critical-medicines" data-i18n="aboutSrcEmaLink">EMA Union list of critical medicines</a></p>
<p data-i18n="aboutSrcChanged">We selected, joined and changed the data. Neither Fimea nor EMA endorses the result.</p><p data-i18n="aboutSrcTimes">Source times show when files were last changed. The publishers give no release times.</p><p data-i18n="aboutSrcArchive">Older history comes from Internet Archive captures.</p></div></details>
<details class="fold"><summary data-i18n="aboutShowsTitle">What the data shows</summary><div><ul class="steps"><li data-i18n="aboutShows1">Packages that companies report as short, with the start date and the company’s estimated end date.</li><li data-i18n="aboutShows2">A label for each package: is another package of the same substitution group on the market?</li><li data-i18n="aboutShows3">Which shortages are on the EU list of critical medicines.</li><li data-i18n="aboutShows4">How the list changes over time.</li></ul></div></details>
<details class="fold"><summary data-i18n="aboutLimTitle">Limits</summary><div><ul class="steps"><li data-i18n="aboutLim1">Companies report shortages. A report can be late or wrong.</li><li data-i18n="aboutLim2">The list does not show stock. A pharmacy may have a package that the list shows as short.</li><li data-i18n="aboutLim3">A package that leaves the list is not proof that supply is back.</li><li data-i18n="aboutLim4">Older history has gaps. Dates are capture dates.</li><li data-i18n="aboutLim5">An alternative on this site is another package in the same substitution group. A pharmacist or doctor decides what you take.</li></ul></div></details></section>
<section id="what-to-do" aria-labelledby="h-what-to-do"><h2 id="h-what-to-do" data-i18n="pathAdvice">What to do if your medicine is short</h2><p data-i18n="doIntro">These steps are general information. They are not medical advice.</p>
<ul class="steps"><li data-i18n="doCheck">Check the package. The list shows single packages, so compare the strength and pack size with your box.</li><li data-i18n="doAsk">Ask your pharmacy. A pharmacist can check what is available, order it, or suggest another package.</li><li data-i18n="doSubst">Another package may be possible. If your medicine is in a substitution group, your pharmacy can offer an interchangeable one. You or your doctor can decide against a change.</li><li data-i18n="doDoctor">Do not stop or change your medicine on your own. If your pharmacy cannot help, contact your doctor, who can prescribe another medicine.</li><li data-i18n="doUrgent">If you feel unwell, contact health care. In an emergency, call 112.</li></ul></section>
<section id="substitution" aria-labelledby="h-subst"><h2 id="h-subst" data-i18n="substTitle">Substitution groups</h2><p data-i18n="aboutGroup">Fimea keeps a list of interchangeable medicines with the same active substance and strength and a similar form. A pharmacy can change a medicine to an interchangeable one and tell you which packages are available; you or your doctor can decide against a change. A group does not guarantee that every package fits you.</p><p><a id="about-group-link" href="https://fimea.fi/en/marketing_authorisations/interchangeable_medicinal_products" data-fimea="group" data-i18n="aboutGroupLink">Fimea’s interchangeable medicines</a></p><p><span data-i18n="fimeaSearchText">To check a package in the source, use Fimea’s own search.</span> <a href="https://fimea.fi/en/databases_and_registers/shortages" data-fimea="search" data-i18n="moreInfoLink">Fimea’s shortage search</a></p></section>
<section id="impact" aria-labelledby="h-impact"><h2 id="h-impact" data-i18n="impactTitle">What the impact label means</h2><p data-i18n="impactAbout">Each shortage gets one label. It tells you whether a pharmacy can usually change the package to an interchangeable one. The label comes from Fimea’s substitution groups and its basic register.</p>
<ul class="impact-levels"><li class="impact-substitute"><svg class="uicon" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false">{IMPACT_ICONS['substitute']}</svg><span data-i18n="aboutImpact_substitute">Substitute usually available: other packages in the same substitution group are on the market and not short. The pharmacy can usually offer one.</span></li>
<li class="impact-critical"><svg class="uicon" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false">{IMPACT_ICONS['critical']}</svg><span data-i18n="aboutImpact_critical">No interchangeable product on the market: the package has a substitution group, but no other package in it is on the market without a shortage. This does not mean that there is no treatment. Talk to your pharmacist or doctor early.</span></li>
<li class="impact-nogroup"><svg class="uicon" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false">{IMPACT_ICONS['nogroup']}</svg><span data-i18n="aboutImpact_nogroup">No substitution group: the pharmacy cannot change the medicine on its own. This is common for hospital medicines and medicines from one company. Ask your pharmacist.</span></li>
<li class="impact-vet"><svg class="uicon" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false"><circle cx="6.500" cy="10.500" r="1.800"/><circle cx="10" cy="6" r="1.800"/><circle cx="14.500" cy="6" r="1.800"/><circle cx="18" cy="10.500" r="1.800"/><path d="M12 12c-2.500 0-4.500 2.800-4.500 5 0 1.500 1.200 2.500 2.500 2.500.8 0 1.300-.4 2-.4s1.200.4 2 .4c1.300 0 2.500-1 2.500-2.500 0-2.200-2-5-4.500-5z"/></svg><span data-i18n="aboutImpact_vet">Veterinary medicines: substitution groups are for human medicines. They are counted apart.</span></li></ul>
<h3 data-i18n="impactCaveatsTitle">Limits of the label</h3>
<ul class="steps"><li data-i18n="impactCaveat1">“On the market” means that the register lists the package as marketed in Finland. It is not a stock check. Your pharmacy may not have it today.</li><li data-i18n="impactCaveatRule">One rule decides what an available alternative is, both for today’s labels and for the history of groups newly without an interchangeable product: another package of the same group that is not on the shortage list and is on the market by its market dates. For today, the register’s own flags must agree: marked as marketed and not marked short. The register has no earlier flags, so earlier captures use the market dates; a package with no entry date is read by today’s market flag.</li><li data-i18n="impactCaveat2">A substitute can also be short in your area, or run out when many people need it at once.</li><li data-i18n="impactCaveat3">Combining strengths, such as two 10 mg tablets for one 20 mg tablet, or changing to another medicine is your doctor’s decision.</li><li data-i18n="impactCaveat4">The label is information, not medical advice. Ask a pharmacist or doctor about your medicines.</li></ul></section>
<section id="how" aria-labelledby="h-how"><h2 id="h-how" data-i18n="howTitle2">How the data works</h2><h3 data-i18n="aboutSourceTitle">Where the data comes from</h3><p data-i18n="aboutSource">The list comes from Fimea, the Finnish Medicines Agency, which publishes it as open data. The archive checks Fimea’s file every day. {ARCHIVE_NOTE}</p><p data-i18n="howUpdate">A scheduled job checks Fimea’s file four times a day and saves a dated copy when it changes. The site is rebuilt from these copies every day.</p><h3 data-i18n="aboutRecordTitle">What one record is</h3><p data-i18n="aboutRecord">One record is one medicine package. The company that holds the marketing authorisation reported it to Fimea. A medicine can have several packages, so the counts are records, not medicines.</p><h3 data-i18n="ledgerTitle">Daily ledger</h3><p data-i18n="ledgerText">Once a day the archive adds rows to a ledger: one row for each package on Fimea’s list, with its VNR, substitution group, impact label, number of alternatives, the date of the register used, and a SHA-256 fingerprint of each source file. Rows are only added, never changed. The first check of a day writes that day. Later checks on the same day add nothing. The ledger records what the files said on that day, so it does not depend on a later register. A day without rows was not recorded. There is one file for each month: data/ledger/YYYY-MM.jsonl.</p><p><a href="https://github.com/AlejandroRenalias/shortage-radar/tree/main/data/ledger" data-i18n="ledgerLink">Open the ledger files</a></p></section>
<section id="limits" aria-labelledby="h-limits"><h2 id="h-limits" data-i18n="limitsTitle">What the data cannot tell you</h2><p data-i18n="aboutLimits">A record that leaves the list is not proof that the medicine is back in supply. The history from before this site started saving the file comes from the Internet Archive and has gaps. Dates in the history are capture dates, not exact event dates. When two captures are more than 14 days apart, nothing is known about the days between them: a notice listed on both sides is shown as “Not observed between” those dates, not as listed throughout.</p><p><strong data-i18n="noticeTitle">Not medical advice.</strong> <span data-i18n="aboutAdvice">This site does not tell you what to take or whether a medicine is available. Ask a pharmacist or doctor about your medicines.</span></p></section>
<section id="downloads" aria-labelledby="h-downloads"><h2 id="h-downloads" data-i18n="downloadsTitle">Downloads</h2><p data-i18n="downloadsText">The data is free to use with credit to Fimea.</p><ul class="links"><li><a href="shortages.csv" data-i18n="dlCsv">Current shortages as a table (CSV)</a></li><li><a href="data.json" data-i18n="dlJson">Full data with event history (JSON)</a></li><li><a href="feed.xml" data-i18n="dlFeedEn">Changes of the last 14 days, English (Atom feed)</a></li><li><a href="feed-fi.xml" data-i18n="dlFeedFi">Changes of the last 14 days, Finnish (Atom feed)</a></li></ul></section>
<section id="cite" aria-labelledby="h-cite"><h2 id="h-cite" data-i18n="citeTitle">Cite this site</h2><p id="citation" class="citation"></p><button type="button" class="btn" id="copy-cite" data-i18n="copyCite">Copy citation</button> <span id="copy-status" role="status"></span><p data-i18n="aboutCite">Fimea’s data is licensed under CC BY 4.0. This site selects, joins and transforms it.</p></section>
<section id="privacy" aria-labelledby="h-privacy"><h2 id="h-privacy" data-i18n="privacyTitle">Privacy</h2><p data-i18n="privacyText">This site has no tracking and no cookies. It uses no analytics, no ads and no outside services. Your language choice is saved on your own device so the site opens in the same language next time. Nothing is sent to anyone.</p></section>
<section id="licence" aria-labelledby="h-licence"><h2 id="h-licence" data-i18n="licenceTitle">Licence</h2><p data-i18n="licenceText">Code: MIT licence. Data: Fimea, CC BY 4.0, selected, joined and transformed by this site. Fonts: Atkinson Hyperlegible Next and Public Sans (digits), SIL Open Font License.</p><p><a href="https://github.com/AlejandroRenalias/shortage-radar" data-i18n="aboutGithub">Code, data files and method on GitHub</a></p></section>
<section id="feedback" aria-labelledby="h-feedback"><h2 id="h-feedback" data-i18n="feedbackTitle">Feedback</h2><p data-i18n="feedbackText">Did you find an error? Open a report on GitHub. You need a GitHub account. The form asks for the page link, what is wrong and a source.</p><p data-i18n="feedbackPublic">Reports are public. Do not write personal or health details.</p><p><a class="btn" href="https://github.com/AlejandroRenalias/shortage-radar/issues/new?template=error-report.yml" data-i18n="feedbackLink">Report an error on GitHub</a></p></section>
</div></div>
<div class="wrap">{load_error()}</div>'''


def not_found():
    return '''<div class="wrap page-head narrow"><h1 data-i18n="nfPageTitle">Page not found</h1><p class="lead" data-i18n="nfPageText">The page you requested could not be found. Try the shortage list, or go back to the start.</p>
<p><a class="btn" href="/shortage-radar/shortages.html" data-i18n="nfSearch">Search the shortage list</a> <a class="btn-quiet" href="/shortage-radar/index.html" data-i18n="navHome">Home</a></p></div>'''


def render_pages(count, impact=None, critical=None, soon=0):
    """Return {file name: html} for every page; `count` is the number of shortages that have started and `soon` the number
    expected within two weeks, shown in the home headline,
    and `impact` the counts by impact level ({'substitute': n, ...}) for the triage on the home page."""
    out = {}
    for key, meta in PAGES.items():
        if meta.get('own'):
            continue
        body = {'index': lambda: home(count, impact, soon), 'shortages': shortages, 'trends': trends, 'about': about, 'medicine': medicine, 'medicines': medicines}[key]()
        meta = dict(meta, script={'index': 'home.js'}.get(key, f'{key}.js'))
        out[meta['file']] = document(key, body, meta=meta)
    prefix = '/shortage-radar/'
    nf = {'file': '404.html', 'title': 'Page not found | Shortage Radar', 'description': 'The page you requested could not be found.', 'form_action': "'none'", 'script': 'common.js'}
    out['404.html'] = document('404', not_found(), prefix, nf)
    if critical:
        from critical_pages import render_critical  # imported here: that module imports this one
        out.update(render_critical(critical))
    return out
