"""Static pages for the site: one shared header and footer, five page bodies and the 404 page.

The English text here is the no-script text. site/i18n.js holds the same text for English and Finnish,
and tests/test_pages.py checks that the two agree, so a string is only ever changed in one idea.
"""
from html import escape

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
               'description': 'How many medicine shortages Finland has had over time, what changed this week, and which groups and companies are most affected.', 'form_action': "'none'"},
    'about': {'file': 'about.html', 'nav': 'navAbout', 'icon': 'info', 'title': 'About the data | Shortage Radar',
              'description': 'What a medicine shortage is, what to do about one, and how this site gets and uses Fimea’s open data.', 'form_action': "'none'"},
    'medicine': {'file': 'medicine.html', 'nav': None, 'icon': None, 'title': 'Medicine | Shortage Radar',
                 'description': 'One medicine package on Fimea’s shortage list: status, timeline and what to do.', 'form_action': "'self'"},
}
NAV_LABELS = {'navHome': 'Home', 'navShortages': 'Shortages', 'navTrends': 'Trends', 'navAbout': 'About'}
NAV_ICONS = {
    'home': '<path d="M3.500 11 12 4l8.500 7M6 9.500V20h12V9.500"/>',
    'list': '<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
    'chart': '<path d="M4 20V4M4 20h16M8 15l3-4 3 2 5-7"/>',
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
            f'<link rel="preload" href="{prefix}fonts/atkinson-latin.woff2" as="font" type="font/woff2" crossorigin>\n'
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
            '<div class="lang" role="group" aria-label="Language" data-i18n-attr="aria-label=languageLabel"><button type="button" lang="fi" data-lang-btn="fi" aria-pressed="false">Suomi</button><button type="button" lang="en" data-lang-btn="en" aria-pressed="false">English</button></div>'
            '</div></header>\n'
            '<div class="stale" id="stale" hidden><div class="wrap"><svg class="uicon" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path d="M12 3.500 2.500 20h19z"/><path d="M12 10v4.500M12 17.500h.01"/></svg><p id="stale-text"></p></div></div>')


def footer(prefix):
    pages = ''.join(f'<li><a href="{prefix}{m["file"]}" data-i18n="{m["nav"]}">{NAV_LABELS[m["nav"]]}</a></li>' for m in PAGES.values() if m['nav'])
    return ('<footer class="site-footer"><div class="wrap foot"><div class="foot-about">'
            f'<p class="foot-brand">{MARK}<span data-i18n="brand">Shortage Radar</span></p>'
            '<p data-i18n="footerTag">Reported medicine shortages in Finland, from Fimea open data. Not medical advice.</p>'
            '<p><span data-i18n="footerAgency">Finnish Medicines Agency Fimea</span>, <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. <span data-i18n="footerTransform">Data was selected, joined and transformed.</span></p>'
            '<p><span data-i18n="archiveCredit">Earlier captures:</span> <a href="https://web.archive.org/">Internet Archive (web.archive.org)</a></p>'
            '<p id="source-times" class="foot-times"></p><p class="foot-times" data-i18n="footerNote">Source times show when the files were last modified; the publisher does not provide release times.</p></div>'
            f'<div><h2 class="foot-title" data-i18n="footerPages">Pages</h2><ul>{pages}</ul></div>'
            f'<div><h2 class="foot-title" data-i18n="footerData">Data</h2><ul><li><a href="{prefix}shortages.csv" data-i18n="footerCsv">Table (CSV)</a></li><li><a href="{prefix}data.json" data-i18n="footerJson">Full data (JSON)</a></li>'
            f'<li><a href="{prefix}feed.xml" data-feed data-i18n="footerFeed">Changes (feed)</a></li><li><a href="https://fimea.fi/en/about_us/open-data" data-fimea="data" data-i18n="sourceLink">Source and licence</a></li></ul></div>'
            '</div></footer>')


def document(page, body, prefix='', meta=None):
    meta = meta or PAGES[page]
    skip = f'<a class="skip-link" href="#main" data-i18n="skip">Skip to content</a>'
    noscript = '<noscript><p class="noscript">JavaScript is needed to show the shortage data. / Saatavuustietojen näyttäminen edellyttää JavaScriptiä.</p></noscript>'
    return (f'<!doctype html>\n<html lang="en" data-page="{page}">\n{head(page, prefix, meta)}\n<body>\n{skip}\n{header(page, prefix)}\n{noscript}\n'
            f'<main id="main" tabindex="-1">\n{body}\n</main>\n{footer(prefix)}\n</body></html>\n')


def load_error(extra=''):
    return f'<p class="state" id="load-error" hidden>Data could not be loaded. Try again later. / Tietoja ei voitu ladata. Yritä myöhemmin uudelleen. <a href="https://fimea.fi/en/about_us/open-data">Fimea</a></p>{extra}'


def search_icon():
    return '<svg class="uicon" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="7"/><path d="m16.500 16.500 4 4"/></svg>'


def home(count):
    line = f'Fimea lists {count:,} {"package" if count == 1 else "packages"} as short today.'
    return f'''<section class="hero wrap"><div class="hero-grid"><div>
<h1 id="hero-line" data-count="{count}">{line}</h1>
<p class="lead" id="hero-sub" data-i18n="heroSub">Includes shortages that have started and ones expected within two weeks. A listing does not tell you whether a medicine is available at your pharmacy.</p>
<form class="bigsearch" action="shortages.html" method="get" role="search">
<label for="q" data-i18n="homeSearchLabel">Search for your medicine</label>
<div class="searchrow">{search_icon()}<input id="q" name="q" type="search" autocomplete="off" maxlength="100" placeholder="e.g. Burana or ibuprofen" data-i18n-attr="placeholder=placeholder"><button type="submit" class="btn" data-i18n="searchButton">Search</button></div>
<p class="hint" data-i18n="hint">Search by medicine, active substance, ATC, company or VNR.</p>
</form></div>
<section class="hero-cards" aria-labelledby="newest-title"><h2 id="newest-title" data-i18n="heroNewest">Newest on the list</h2><div id="newest" class="pkg-list"></div></section>
</div></section>
<section class="facts-band" aria-labelledby="facts-title"><div class="wrap">
<div class="facts-head"><h2 id="facts-title">This week</h2><p id="facts-since"></p></div>
<dl class="facts" id="facts"></dl>
</div></section>
<section class="wrap paths" aria-labelledby="paths-title">
<h2 id="paths-title" class="sr-only" data-i18n="pathsTitle">Where to next</h2>
<a class="path path-main" href="shortages.html"><svg class="uicon" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="7"/><path d="m16.500 16.500 4 4"/></svg><span><strong data-i18n="pathFind">Find a medicine</strong><span data-i18n="pathFindText">Search the full list and filter it by group, form and company.</span></span></a>
<a class="path" href="trends.html"><svg class="uicon" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" focusable="false"><path d="M4 20V4M4 20h16M8 15l3-4 3 2 5-7"/></svg><span><strong data-i18n="pathTrends">See trends</strong><span data-i18n="pathTrendsText">How many shortages there are and how that has changed.</span></span></a>
<a class="path" href="about.html#what-to-do"><svg class="uicon" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" focusable="false"><path d="M12 4v16M4 12h16"/><rect x="3" y="3" width="18" height="18" rx="5"/></svg><span><strong data-i18n="pathAdvice">What to do if your medicine is short</strong><span data-i18n="pathAdviceText">Short steps for patients and relatives.</span></span></a>
</section>
{load_error()}'''


def shortages():
    return f'''<div class="wrap page-head"><h1 data-i18n="listTitle">Medicine shortages</h1><p class="lead" data-i18n="listIntro">Every package Fimea lists as short or soon to be short. Open a package to see its timeline.</p></div>
<div class="wrap finder">
<form id="finder" role="search" novalidate>
<label class="sr-only" for="search" data-i18n="searchLabel">Search shortages</label>
<div class="searchrow">{search_icon()}<input id="search" type="search" autocomplete="off" maxlength="100" placeholder="e.g. Burana or ibuprofen" data-i18n-attr="placeholder=placeholder"></div>
<p class="hint" id="search-hint" data-i18n="hint">Search by medicine, active substance, ATC, company or VNR.</p>
<details class="filters" id="filters"><summary><span data-i18n="filters">Filters</span><span id="filters-count"></span></summary>
<div class="filter-grid">
<fieldset class="seg"><legend data-i18n="filterStatus">Status</legend>
<label><input type="radio" name="status" value="" checked><span data-i18n="statusAll">All</span></label>
<label><input type="radio" name="status" value="now"><span data-i18n="statusNow">Shortage now</span></label>
<label><input type="radio" name="status" value="soon"><span data-i18n="statusSoon">Starting soon</span></label></fieldset>
<div class="field"><label for="f-group" data-i18n="filterGroup">Medicine group</label><select id="f-group"></select></div>
<div class="field"><label for="f-form" data-i18n="filterForm">Form</label><select id="f-form"></select></div>
<div class="field"><label for="f-company" data-i18n="filterCompany">Company</label><select id="f-company"></select></div>
<div class="field"><label for="sort" data-i18n="sortLabel">Sort by</label><select id="sort"><option value="" data-i18n="sortDefault">Current first</option><option value="name" data-i18n="sortName">Name</option><option value="longest" data-i18n="sortLongest">Longest running</option><option value="end" data-i18n="sortEnd">Expected back soonest</option></select></div>
<button type="button" class="btn-quiet" id="clear" data-i18n="clearFilters" hidden>Clear filters</button>
</div></details>
</form>
</div>
<div class="wrap results">
<div class="list-meta"><p id="result-count" aria-live="polite" aria-atomic="true"></p><button type="button" class="btn-quiet" id="copy-link" data-i18n="copyLink">Copy link to this search</button><span id="copy-status" role="status"></span></div>
<div id="list" class="pkg-list"><p class="state" id="loading">Loading…</p></div>
<div class="more"><p id="more-count"></p><button type="button" class="btn" id="more" data-i18n="more" hidden>Show more</button></div>
{load_error()}
</div>'''


def medicine():
    return f'''<div class="wrap" id="medicine"><p class="state" id="loading">Loading…</p></div>
<div class="wrap">{load_error()}</div>'''


def trends():
    return f'''<div class="wrap page-head"><h1 data-i18n="trendsTitle">Trends</h1><p class="lead" data-i18n="trendsIntro">How many packages Fimea lists as short, and how that has changed.</p><p class="data-date" id="data-date"></p></div>
<div class="wrap trend-grid">
<section class="panel panel-wide" aria-labelledby="chart-title"><h2 id="chart-title" data-i18n="chartTitle">Packages on the list over time</h2><p id="history-note" class="note"></p><div id="chart" class="chart"></div><p id="rss-note" class="note"></p>
<details class="data-table"><summary data-i18n="tableToggle">Show the chart data as a table</summary><div id="chart-table"></div></details></section>
<section class="panel" id="week" aria-labelledby="week-title"><h2 id="week-title" data-i18n="weekTitle">This week</h2><p id="week-window" class="note"></p><dl class="mini-facts" id="week-facts"></dl><p><a id="feed-link" href="feed.xml" data-feed data-i18n="feedLink">Follow changes (feed)</a></p></section>
<section class="panel" aria-labelledby="longest-title"><h2 id="longest-title" data-i18n="longestTitle">Longest running current shortages</h2><p class="note" data-i18n="longestNote">Time since the reported start date.</p><ol id="longest-list" class="longest"></ol></section>
<section class="panel" aria-labelledby="group-title"><h2 id="group-title" data-i18n="byGroup">By medicine group</h2><p class="note" data-i18n="byGroupNote">Packages on the list, by medicine group.</p><div id="atc"></div></section>
<section class="panel" aria-labelledby="company-title"><h2 id="company-title" data-i18n="byCompany">By company</h2><p class="note" data-i18n="byCompanyNote">The ten companies with the most packages on the list.</p><div id="company"></div></section>
<section class="panel panel-wide" aria-labelledby="delay-title"><h2 id="delay-title" data-i18n="delayTitle">Did shortages leave the list by the estimated date?</h2><p id="delay-headline" class="big-note"></p><div id="delay-visual"></div><p id="delay-note" class="note">Needs more weeks of data.</p><div class="how-count" id="how-count" hidden><h3 data-i18n="howTitle">How we count</h3><p id="how-count-text"></p></div><div id="delay-list"></div></section>
<section class="panel panel-wide cite" id="cite-box" aria-labelledby="cite-title" hidden><h2 id="cite-title" data-i18n="citeTitle">Cite this site</h2><p class="note" data-i18n="citeIntro">Use the data date and the source when you cite these figures.</p><p id="citation" class="citation"></p><button type="button" class="btn" id="copy-cite" data-i18n="copyCite">Copy citation</button> <span id="copy-status" role="status"></span></section>
</div>
<div class="wrap">{load_error()}</div>'''


def about():
    return f'''<div class="wrap page-head"><h1 data-i18n="aboutH1">About the data</h1><p class="lead" data-i18n="aboutIntro">What a shortage is, what to do about one, and how this site works.</p></div>
<div class="wrap about-layout">
<nav class="toc" aria-labelledby="toc-title"><p id="toc-title" class="toc-title" data-i18n="aboutToc">On this page</p><ul>
<li><a href="#what-is" data-i18n="helpTitle">What is a shortage?</a></li><li><a href="#what-to-do" data-i18n="pathAdvice">What to do if your medicine is short</a></li><li><a href="#substitution" data-i18n="substTitle">Substitution groups</a></li><li><a href="#how" data-i18n="howTitle2">How the data works</a></li><li><a href="#limits" data-i18n="limitsTitle">What the data cannot tell you</a></li><li><a href="#downloads" data-i18n="downloadsTitle">Downloads</a></li><li><a href="#cite" data-i18n="citeTitle">Cite this site</a></li><li><a href="#privacy" data-i18n="privacyTitle">Privacy</a></li><li><a href="#licence" data-i18n="licenceTitle">Licence</a></li><li><a href="#report" data-i18n="reportTitle">Report a data problem</a></li></ul></nav>
<div class="prose">
<section id="what-is" aria-labelledby="h-what-is"><h2 id="h-what-is" data-i18n="helpTitle">What is a shortage?</h2><p data-i18n="help">The company has told Fimea it cannot deliver this package for a while. Your pharmacy may still have some. Ask your pharmacy what is available.</p></section>
<section id="what-to-do" aria-labelledby="h-what-to-do"><h2 id="h-what-to-do" data-i18n="pathAdvice">What to do if your medicine is short</h2><p data-i18n="doIntro">These steps are general information. They are not medical advice.</p>
<ul class="steps"><li data-i18n="doCheck">Check the package. The list shows single packages, so compare the strength and pack size with your box.</li><li data-i18n="doAsk">Ask your pharmacy. A pharmacist can check what is available, order it, or suggest another package.</li><li data-i18n="doSubst">Another package may be possible. If your medicine is in a substitution group, your pharmacy can offer an interchangeable one. You or your doctor can decide against a change.</li><li data-i18n="doDoctor">Do not stop or change your medicine on your own. If your pharmacy cannot help, contact your doctor, who can prescribe another medicine.</li><li data-i18n="doUrgent">If you feel unwell, contact health care. In an emergency, call 112.</li></ul></section>
<section id="substitution" aria-labelledby="h-subst"><h2 id="h-subst" data-i18n="substTitle">Substitution groups</h2><p data-i18n="aboutGroup">Fimea keeps a list of interchangeable medicines with the same active substance and strength and a similar form. A pharmacy can change a medicine to an interchangeable one and tell you which packages are available; you or your doctor can decide against a change. A group does not guarantee that every package fits you.</p><p><a id="about-group-link" href="https://fimea.fi/en/marketing_authorisations/interchangeable_medicinal_products" data-fimea="group" data-i18n="aboutGroupLink">Fimea’s interchangeable medicines</a></p><p><span data-i18n="fimeaSearchText">To check a package in the source, use Fimea’s own search.</span> <a href="https://fimea.fi/en/databases_and_registers/shortages" data-fimea="search" data-i18n="moreInfoLink">Fimea’s shortage search</a></p></section>
<section id="how" aria-labelledby="h-how"><h2 id="h-how" data-i18n="howTitle2">How the data works</h2><h3 data-i18n="aboutSourceTitle">Where the data comes from</h3><p data-i18n="aboutSource">The list comes from Fimea, the Finnish Medicines Agency, which publishes it as open data. The archive checks Fimea’s file every day. {ARCHIVE_NOTE}</p><p data-i18n="howUpdate">A scheduled job checks Fimea’s file four times a day and saves a dated copy when it changes. The site is rebuilt from these copies every day.</p><h3 data-i18n="aboutRecordTitle">What one record is</h3><p data-i18n="aboutRecord">One record is one medicine package. The company that holds the marketing authorisation reported it to Fimea. A medicine can have several packages, so the counts are records, not medicines.</p></section>
<section id="limits" aria-labelledby="h-limits"><h2 id="h-limits" data-i18n="limitsTitle">What the data cannot tell you</h2><p data-i18n="aboutLimits">A record that leaves the list is not proof that the medicine is back in supply. The history from before this site started saving the file comes from the Internet Archive and has gaps. Dates in the history are capture dates, not exact event dates.</p><p><strong data-i18n="noticeTitle">Not medical advice.</strong> <span data-i18n="aboutAdvice">This site does not tell you what to take or whether a medicine is available. Ask a pharmacist or doctor about your medicines.</span></p></section>
<section id="downloads" aria-labelledby="h-downloads"><h2 id="h-downloads" data-i18n="downloadsTitle">Downloads</h2><p data-i18n="downloadsText">The data is free to use with credit to Fimea.</p><ul class="links"><li><a href="shortages.csv" data-i18n="dlCsv">Current shortages as a table (CSV)</a></li><li><a href="data.json" data-i18n="dlJson">Full data with event history (JSON)</a></li><li><a href="feed.xml" data-i18n="dlFeedEn">Changes of the last 14 days, English (Atom feed)</a></li><li><a href="feed-fi.xml" data-i18n="dlFeedFi">Changes of the last 14 days, Finnish (Atom feed)</a></li></ul></section>
<section id="cite" aria-labelledby="h-cite"><h2 id="h-cite" data-i18n="citeTitle">Cite this site</h2><p id="citation" class="citation"></p><button type="button" class="btn" id="copy-cite" data-i18n="copyCite">Copy citation</button> <span id="copy-status" role="status"></span><p data-i18n="aboutCite">Fimea’s data is licensed under CC BY 4.0. This site selects, joins and transforms it.</p></section>
<section id="privacy" aria-labelledby="h-privacy"><h2 id="h-privacy" data-i18n="privacyTitle">Privacy</h2><p data-i18n="privacyText">This site has no tracking and no cookies. It uses no analytics, no ads and no outside services. Your language choice is saved on your own device so the site opens in the same language next time. Nothing is sent to anyone.</p></section>
<section id="licence" aria-labelledby="h-licence"><h2 id="h-licence" data-i18n="licenceTitle">Licence</h2><p data-i18n="licenceText">Code: MIT licence. Data: Fimea, CC BY 4.0, selected, joined and transformed by this site. Font: Atkinson Hyperlegible Next, SIL Open Font License.</p><p><a href="https://github.com/AlejandroRenalias/shortage-radar" data-i18n="aboutGithub">Code, data files and method on GitHub</a></p></section>
<section id="report" aria-labelledby="h-report"><h2 id="h-report" data-i18n="reportTitle">Report a data problem</h2><p data-i18n="reportText">If a date, a name or a number looks wrong, tell us. Include the VNR if you can.</p><p><a href="https://github.com/AlejandroRenalias/shortage-radar/issues/new?template=data-problem.yml" data-i18n="reportProblem">Report a data problem</a></p></section>
</div></div>
<div class="wrap">{load_error()}</div>'''


def not_found():
    return '''<div class="wrap page-head narrow"><h1 data-i18n="nfPageTitle">Page not found</h1><p class="lead" data-i18n="nfPageText">The page you requested could not be found. Try the shortage list, or go back to the start.</p>
<p><a class="btn" href="/shortage-radar/shortages.html" data-i18n="nfSearch">Search the shortage list</a> <a class="btn-quiet" href="/shortage-radar/index.html" data-i18n="navHome">Home</a></p></div>'''


def render_pages(count):
    """Return {file name: html} for every page; `count` is the number of current shortages, shown in the home headline."""
    out = {}
    for key, meta in PAGES.items():
        body = {'index': lambda: home(count), 'shortages': shortages, 'trends': trends, 'about': about, 'medicine': medicine}[key]()
        meta = dict(meta, script={'index': 'home.js'}.get(key, f'{key}.js'))
        out[meta['file']] = document(key, body, meta=meta)
    prefix = '/shortage-radar/'
    nf = {'file': '404.html', 'title': 'Page not found | Shortage Radar', 'description': 'The page you requested could not be found.', 'form_action': "'none'", 'script': 'common.js'}
    out['404.html'] = document('404', not_found(), prefix, nf)
    return out
