"""Pages for "Critical medicines in Finland": the match page, the methods page and one page for every code on the EU list.

The pages are plain HTML written at build time, so they work without scripts; `site/critical.js` only adds a filter.
They are in English only. Facts only: no advice, no score, no forecast.
"""
from html import escape

from changes import date_text
from critical import STATUS_NAMES, TYPE_NAMES, TYPES, credit
from pages import SITE_URL, document

E = lambda value: escape(str(value if value is not None else ''), quote=True)
D = lambda value: date_text(value, 'en') or 'not given'
FIMEA_LICENCE = 'https://fimea.fi/en/about_us/open-data'
EMA_NOTICE = 'https://www.ema.europa.eu/en/about-us/legal-notice'
EMA_LIST = 'https://www.ema.europa.eu/en/human-regulatory-overview/post-authorisation/medicine-shortages-availability-issues/availability-medicines-during-crises/union-list-critical-medicines'
TYPE_EXPLAINED = {
    'exact': 'The ATC code is on the EU list, the active ingredient is the list substance and a route of the product fits a route of the list row.',
    'route-mismatch': 'The ATC code and ingredient are on the EU list, but no route of the product fits the list row, or Fimea gives no usable route.',
    'ingredient-mismatch': 'The ATC code is on the EU list, but the list substance is not among the active ingredients of the product, or no ingredients are given.',
    'unmatched': 'The VNR is not in the Fimea register, so the code is not known.',
}
FILE = {'critical': 'critical.html', 'methods': 'critical-methods.html'}


def code_file(atc):
    return f'critical-{atc}.html'


def meta_for(file, title, description, script='common.js'):
    return {'file': file, 'nav': None, 'title': title, 'description': description, 'form_action': "'none'", 'script': script}


def chip(match_type):
    return f'<span class="eu-chip eu-{match_type}">{E(TYPE_NAMES.get(match_type, "Flagged by Fimea only"))}</span>'


def name_cell(r):
    name = ' '.join(x for x in (r.get('name'), r.get('strength')) if x) or f"VNR {r['vnr']}"
    sub = r.get('substances') or ''
    form = r.get('form_en') or r.get('form') or ''
    detail = ', '.join(x for x in (sub, form) if x)
    return f'<strong>{E(name)}</strong>' + (f'<span class="note">{E(detail)}</span>' if detail else '')


def route_cell(r):
    if r['match_type'] == 'unmatched':
        return '<span class="note">not known</span>'
    product = ', '.join(r.get('product_routes') or []) or 'not given'
    return f'<span><span class="eu-route"><b>Product:</b> {E(product)}</span><span class="eu-route"><b>List:</b> {E(r.get("list_route") or "—")}</span></span>'


def status_cell(r):
    """Fimea's Voimassa: K is ongoing, E has not started yet; the start date shows when."""
    if r['status'] == 'ongoing':
        return f'<span>Ongoing<span class="note">since {E(D(r["start"]))}</span></span>'
    return f'<span>Starts later<span class="note">on {E(D(r["start"]))}</span></span>'


def notice_row(r):
    atc = f'<a href="{code_file(r["atc"])}">{E(r["atc"])}</a>' if r.get('atc') and r['match_type'] != 'flag-only' else E(r.get('atc') or '—')
    text = ' '.join(str(r.get(k, '')) for k in ('vnr', 'atc', 'name', 'substances', 'company', 'list_description')).casefold()
    return (f'<tr data-type="{E(r["match_type"])}" data-status="{r["status"]}" data-text="{E(text)}"><td data-label="Medicine">{name_cell(r)}<span class="eu-note">{E(r["note"])}</span></td>'
            f'<td data-label="ATC code">{atc}</td><td data-label="Match">{chip(r["match_type"])}</td><td data-label="Status">{status_cell(r)}</td><td data-label="Route">{route_cell(r)}</td>'
            f'<td data-label="Company">{E(r.get("company", ""))}</td><td data-label="Estimated end">{E(D(r.get("end")))}</td><td data-label="VNR">{E(r["vnr"])}</td></tr>')


def downloads():
    return ('<ul class="links"><li><a href="critical.csv">All matches (CSV)</a></li><li><a href="critical.json">All matches (JSON)</a></li>'
            '<li><a href="critical-feed.xml">Alerts: new shortages (RSS)</a></li><li><a href="critical-feed.json">Alerts: new shortages (JSON feed)</a></li></ul>')


def source_block(meta, snapshot_date, source_metadata):
    shortages = (source_metadata or {}).get('shortages_last_modified') or ''
    register = (source_metadata or {}).get('register_last_modified') or ''
    return (f'<p class="note">{E(credit(meta))}</p>'
            f'<p class="note">Shortage file saved {E(D(snapshot_date))}' + (f' (file modified {E(shortages)})' if shortages else '') + '.'
            + (f' Register file modified {E(register)}.' if register else '') + '</p>')


def critical_page(data):
    meta, rows, counts = data['eu']['meta'], data['rows'], data['counts']
    ongoing, upcoming = counts['ongoing'], counts['upcoming']
    tiles = ''.join(
        f'<li class="eu-count eu-{t}"><span class="eu-num">{ongoing[t]:,}</span><span class="eu-label"><strong>{E(TYPE_NAMES[t])}</strong><span>{E(TYPE_EXPLAINED[t])}</span></span></li>'
        for t in TYPES)
    later = {t: upcoming[t] for t in TYPES if upcoming[t]}
    later_line = (f'<p class="note">Not counted above: {sum(later.values()):,} {"package" if sum(later.values()) == 1 else "packages"} that Fimea lists as starting later '
                  f'({"; ".join(f"{n:,} {E(TYPE_NAMES[t]).lower()}" for t, n in later.items())}). They are in the table, marked “Starts later”.</p>') if later else ''
    flag_line = (f'<p class="note">Fimea’s own EU-critical flag differs from this match for {counts["disagree"]:,} ongoing {"package" if counts["disagree"] == 1 else "packages"}'
                 + (f', and Fimea flags {ongoing["flag-only"] + upcoming["flag-only"]:,} more whose ATC code is not on the list' if ongoing['flag-only'] + upcoming['flag-only'] else '') + '. The note on each row says so.</p>')
    body_rows = ''.join(notice_row(r) for r in rows) or '<tr><td colspan="8">No shortage packages match the EU list today.</td></tr>'
    codes = ''.join(
        f'<li><a href="{code_file(a)}"><span class="eu-code">{E(a)}</span> {E(row["description"].title())}</a>'
        + (f' <span class="note">{data["history"][a]["count"]:,} in archive</span>' if a in data['history'] else '') + '</li>'
        for a, row in sorted(data['eu']['rows'].items()))
    body = f'''<div class="wrap page-head"><h1>Critical medicines in Finland</h1>
<p class="lead">Medicines on the EU Union list of critical medicines (version {E(meta['version'])}, {E(D(meta['published']))}) that Fimea lists as short in Finland.</p>
<p class="note"><strong>This is not medical advice.</strong> A listing does not tell you whether a medicine is available at your pharmacy. Ask a pharmacist or doctor about your medicines. <a href="{FILE['methods']}">How the match works</a></p></div>
<section class="wrap" aria-labelledby="eu-counts-title"><h2 id="eu-counts-title" class="sr-only">Counts</h2>
<p class="eu-asof">Ongoing shortages in the Fimea file saved on <strong>{E(D(data['snapshot_date']))}</strong>. Fimea marks a notice as ongoing (Voimassa K) or not yet started (E).</p>
<ul class="eu-counts">{tiles}</ul>{later_line}{flag_line}</section>
<section class="wrap eu-list" aria-labelledby="eu-table-title"><h2 id="eu-table-title">Shortage packages that match the EU list</h2>
<form class="eu-filter needs-js" id="eu-filter"><label for="eu-q">Search</label><input id="eu-q" type="search" autocomplete="off" maxlength="100" placeholder="Name, substance, ATC code, company or VNR">
<label for="eu-type">Match</label><select id="eu-type"><option value="">All matches</option><option value="exact">{E(TYPE_NAMES['exact'])}</option><option value="route-mismatch">{E(TYPE_NAMES['route-mismatch'])}</option><option value="ingredient-mismatch">{E(TYPE_NAMES['ingredient-mismatch'])}</option><option value="unmatched">{E(TYPE_NAMES['unmatched'])}</option></select>
<label for="eu-status">Status</label><select id="eu-status"><option value="">Ongoing and starts later</option><option value="ongoing">Ongoing</option><option value="upcoming">Starts later</option></select>
<p class="note" id="eu-shown" role="status"></p></form>
<div class="eu-scroll"><table class="eu-table"><thead><tr><th scope="col">Medicine</th><th scope="col">ATC code</th><th scope="col">Match</th><th scope="col">Status</th><th scope="col">Route</th><th scope="col">Company</th><th scope="col">Estimated end</th><th scope="col">VNR</th></tr></thead><tbody id="eu-body">{body_rows}</tbody></table></div>
<p class="note">Estimated end dates are the company’s estimates. Fimea’s file keeps no history and its dates can change.</p></section>
<section class="wrap eu-more" aria-labelledby="eu-dl-title"><h2 id="eu-dl-title">Download</h2>{downloads()}
<details class="data-table"><summary>All {len(data['eu']['rows'])} codes on the EU list</summary><ul class="eu-codes">{codes}</ul></details>
{source_block(meta, data['snapshot_date'], data['source_metadata'])}<p class="note">These pages are in English only.</p></section>'''
    return document('critical', body, meta=meta_for(FILE['critical'], 'Critical medicines in Finland | Shortage Radar',
                    'Medicines on the EU Union list of critical medicines that Fimea lists as short in Finland, matched by ATC code and route.', 'critical.js'))


def days_text(n):
    return f'{n} {"day" if n == 1 else "days"}'


def history_block(code, h, archive_start):
    if not h:
        return '<p>No shortage for this code is in our archive.</p>'
    lines = [f'<p>Our archive holds {h["count"]:,} {"shortage" if h["count"] == 1 else "shortages"} for packages with this code since {E(D(archive_start))}: '
             f'{h["listed_now"]:,} listed now, {h["gone"]:,} no longer listed. A notice that Fimea edited, or that was missing from some captures and came back, is counted as one shortage.</p>']
    if h['measured']:
        lines.append(f'<p>For {h["measured"]:,} no longer listed shortages whose start we saw and with no gap in the captures, the days between the first and the last capture that listed them were '
                     f'{E(days_text(h["days_min"]))} at least, {E(days_text(round(h["days_median"])))} in the middle and {E(days_text(h["days_max"]))} at most. '
                     'These are days between captures, not exact lengths: a shortage may have started before the first capture and lasted after the last.</p>')
    else:
        lines.append('<p>No shortage that left the list has a known start and a gap-free record, so no days between captures can be given.</p>')
    rows = []
    for n in h['notices']:
        seen = 'Still listed' if n['removed_on'] is None else f'Last seen {E(D(n["last_seen"]))}'
        first = f'Listed in the first capture ({E(D(n["first_seen"]))})' if n['listed_at_first_capture'] else E(D(n['first_seen']))
        notes = []
        if n['edits']:
            notes.append(f'Notice edited {n["edits"]} {"time" if n["edits"] == 1 else "times"}; counted as one shortage.')
        notes += [f'Not listed in the captures between {E(D(u["from"]))} and {E(D(u["to"]))}: unknown.' for u in n['unseen']]
        notes += [f'No capture for {g["days"]} days ({E(D(g["from"]))} to {E(D(g["to"]))}): unknown.' for g in n['gaps']]
        between = 'unknown' if (n['gaps'] or n['unseen']) else str(n['days_between_captures'])
        rows.append(f'<tr><td data-label="Package">{E(" ".join(x for x in (n["name"], n["strength"]) if x))}<span class="note">VNR {E(n["NordicArticleNumber"])}, {E(n["Company"])}</span>'
                    + ''.join(f'<span class="note">{x}</span>' for x in notes) + '</td>'
                    f'<td data-label="Match">{chip(n["match_type"])}</td><td data-label="Reported start">{E(D(n["UnavailableFrom"]))}</td>'
                    f'<td data-label="First seen">{first}</td><td data-label="Last seen">{seen}</td><td data-label="Days between captures">{between}</td></tr>')
    lines.append('<div class="eu-scroll"><table class="eu-table eu-history"><thead><tr><th scope="col">Package</th><th scope="col">Match</th><th scope="col">Reported start</th><th scope="col">First seen</th><th scope="col">Last seen</th><th scope="col">Days between captures</th></tr></thead>'
                 f'<tbody>{"".join(rows)}</tbody></table></div>')
    lines.append('<p class="note">The archive is made of captures of Fimea’s file, not daily readings; before 21 Nov 2026 the captures come from the Internet Archive and have gaps. '
                 'A gap in the captures is unknown time: it is not a new start and not an end. '
                 '“Last seen” is the last capture that listed the shortage. A shortage that is not listed any more is not proof that supply returned.</p>')
    return ''.join(lines)


def code_page(code, row, data):
    meta = data['eu']['meta']
    notices = [r for r in data['rows'] if r.get('atc') == code]
    current = ''.join(
        f'<li class="eu-card"><div>{name_cell(r)}</div><div>{chip(r["match_type"])}</div><p class="note">{E(r["note"])}</p>'
        f'<dl><dt>Status</dt><dd>{E(STATUS_NAMES[r["status"]])}</dd><dt>Company</dt><dd>{E(r["company"])}</dd><dt>Reported start</dt><dd>{E(D(r["start"]))}</dd><dt>Estimated end</dt><dd>{E(D(r["end"]))}</dd>'
        f'<dt>Notified</dt><dd>{E(D(r["notified"]))}</dd><dt>VNR</dt><dd>{E(r["vnr"])}</dd><dt>Product route</dt><dd>{E(", ".join(r["product_routes"]) or "not given")}</dd></dl></li>'
        for r in notices)
    current = f'<ul class="eu-cards">{current}</ul>' if current else '<p>Fimea lists no shortage package with this code today.</p>'
    title = f'{row["description"].title()} ({code})'
    body = f'''<div class="wrap page-head"><p class="note"><a href="{FILE['critical']}">Critical medicines in Finland</a></p><h1>{E(title)}</h1>
<p class="lead">ATC code {E(code)} is on the EU Union list of critical medicines, version {E(meta['version'])}.</p></div>
<div class="wrap eu-code-page">
<section aria-labelledby="h-list"><h2 id="h-list">EU list row</h2>
<dl class="eu-facts"><dt>ATC code</dt><dd>{E(code)}</dd><dt>Substance on the list</dt><dd>{E(row['description'])}</dd><dt>Routes on the list</dt><dd>{E(row['route'])}</dd>
<dt>Date of inclusion</dt><dd>{E(D(row['included']))}</dd><dt>List version</dt><dd>{E(meta['version'])} ({E(meta['reference'])}, {E(D(meta['published']))})</dd><dt>Row in the EMA file</dt><dd>{row['row']}</dd></dl></section>
<section aria-labelledby="h-now"><h2 id="h-now">Fimea notices today</h2>{current}</section>
<section aria-labelledby="h-history"><h2 id="h-history">Seen in our archive</h2>{history_block(code, data['history'].get(code), data['archive_start'])}</section>
<section><p class="note">This is not medical advice. {E(credit(meta))}</p>{downloads()}<p class="note"><a href="{FILE['methods']}">How the match works</a></p></section></div>'''
    return document('critical', body, meta=meta_for(code_file(code), f'{title} | Critical medicines | Shortage Radar',
                    f'Fimea shortage notices, the EU list row and the archive history for ATC code {code}.'))


def methods_page(data):
    meta = data['eu']['meta']
    checks = [
        ('Desmopressin Sandoz', '416337', 'Route does not fit', 'Product route is under the tongue (Fimea route code 1070). The list row H01BA02 has intramuscular, intravenous and subcutaneous use.'),
        ('Desmopressin STADA', '448525', 'Route does not fit', 'Under the tongue (code 1070), as above.'),
        ('Desmopressin ratiopharm', '485073', 'Route does not fit', 'Under the tongue (code 1070), as above.'),
        ('Miochol-E', '019235', 'Exact match', 'ATC code S01EB09 and the route match the list (intraocular use; Fimea route code 1092, into the front chamber of the eye). Fimea’s own flag is 0, so Fimea and the list differ for this package. The note says so.'),
    ]
    check_rows = ''.join(f'<tr><td data-label="Package">{E(n)}</td><td data-label="VNR">{v}</td><td data-label="Result">{E(t)}</td><td data-label="Why">{E(w)}</td></tr>' for n, v, t, w in checks)
    body = f'''<div class="wrap page-head"><p class="note"><a href="{FILE['critical']}">Critical medicines in Finland</a></p><h1>How the critical medicines match works</h1>
<p class="lead">Which sources we use, how a shortage is matched to the EU list, and what the match cannot tell you.</p></div>
<div class="wrap about-layout"><div class="prose">
<section id="sources"><h2>Sources</h2><ul class="steps">
<li><strong>EU list.</strong> <a href="{EMA_LIST}">Union list of critical medicines</a>, European Medicines Agency (EMA) and the Heads of Medicines Agencies. We use version {E(meta['version'])} ({E(meta['reference'])}, {E(D(meta['published']))}) and keep it fixed. It has {len(data['eu']['rows'])} rows, one for each ATC level 5 code. The route text of a row can name several routes. The file has no dosage form column. We keep the sheet row of each entry.</li>
<li><strong>Fimea shortage file.</strong> <code>Shortages.txt</code> (also published as <code>Saatavuushairiot.txt</code>, with Finnish column names) from <a href="{FIMEA_LICENCE}">Fimea open data</a>. It lists packages by VNR with the company’s start and estimated end dates. Fimea does not keep a history of this file and the dates are estimates. Only products that have a VNR appear.</li>
<li><strong>Fimea basic register.</strong> <code>Perusrekisteri2026.xml</code>, with the ATC code, the dosage form, the route of administration (<code>Antoreitti</code>), the active substances and Fimea’s own flag <code>EUKriittinenValmiste</code>. We read the 225 MB file as a stream.</li>
<li><strong>Dosage form names.</strong> <code>pharmaceutical_form.csv</code> from Fimea. It has form names and translations only. We use it for the English form names we show. It does not decide a match.</li>
<li><strong>Archive.</strong> Our own captures of the shortage file, daily since 21 Nov 2026, and earlier captures from the Internet Archive.</li></ul></section>
<section id="licences"><h2>Licences and credit</h2>
<p><strong>Fimea.</strong> Fimea’s open data is licensed under <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. The licence asks for the name of the licensor, the name of the material and the date and time it was released by Fimea. Fimea does not give release times; we show the file’s last-modified time instead. We select, join and transform the data. Fimea does not endorse this site.</p>
<p><strong>EMA.</strong> EMA’s <a href="{EMA_NOTICE}">copyright notice</a> says its web content may be reproduced and distributed, for non-commercial and commercial purposes, if EMA is always acknowledged as the source. It is not a Creative Commons licence. We show EMA as the source of the list wherever the list is used, including in the downloads.</p>
<p>Source credit used in the downloads: {E(credit(meta))}</p>
<p>Code on this site: MIT licence.</p></section>
<section id="rule"><h2>The match rule</h2><ol class="steps">
<li><strong>ATC code.</strong> The ATC level 5 code of the product in the Fimea register must be exactly a code on the EU list. Fimea gives one ATC code for each product.</li>
<li><strong>Active ingredient.</strong> The substance of the list row must be among the product’s active ingredients (all of them, for a list row that names several, such as piperacillin and tazobactam). A name counts when it is the same, or when the register name starts with it (“Ipratropium bromide” for IPRATROPIUM). A few list names are spelled differently in the register (adrenaline and epinephrine, vaccines, blood products); they are in <a href="https://github.com/AlejandroRenalias/shortage-radar/blob/main/data/critical/ingredients.json"><code>data/critical/ingredients.json</code></a>. Extra ingredients are allowed, so a combination product with the list substance passes. If the substance is not there, or Fimea gives no ingredients, the package is shown as <em>Ingredient not confirmed</em> and is neither an exact match nor an alert. Example: B. Braun sodium chloride (VNR 389066) has the ATC code of potassium chloride and a fitting route, but its ingredient is sodium chloride.</li>
<li><strong>Route.</strong> A route of the product (Fimea <code>Antoreitti</code>) must fit a route of the list row. A table in <a href="https://github.com/AlejandroRenalias/shortage-radar/blob/main/data/critical/routes.json"><code>data/critical/routes.json</code></a> says which Fimea route fits which EU route term. There are no keyword rules. Three broader EU terms are handled in the table: “parenteral use” fits every injection route, “intravascular use” fits a vein or an artery, and “intraocular use” fits routes into the eye (front chamber, vitreous, retina, inside the eye).</li>
<li><strong>Result.</strong> ATC code, ingredient and route fit: <em>Exact match</em>. ATC code and ingredient on the list, route does not fit: <em>Route does not fit</em> (<code>route-mismatch</code> in the downloads). ATC code on the list, ingredient not confirmed: <em>Ingredient not confirmed</em> (<code>ingredient-mismatch</code>). VNR not in the register: <em>Not in the register</em> (<code>unmatched</code>).</li>
<li><strong>Ongoing or starts later.</strong> Fimea marks each notice as ongoing (Voimassa K, “Kyllä”) or not yet started (E, “Ei”). The counts show ongoing shortages only; notices that start later are listed apart, marked “Starts later”, with their start date. The counts carry the date of the shortage file.</li>
<li><strong>Route unclear.</strong> If Fimea gives no route, or only “route not relevant”, or a route that is not in our table, the package is not matched on route. It is shown as <em>Route does not fit</em> and the note says “Route unclear”. We do not guess.</li>
<li><strong>Cross-check.</strong> Fimea’s flag <code>EUKriittinenValmiste</code> is not used to decide. Where it disagrees with the match, the note and the CSV say so.</li></ol></section>
<section id="checked"><h2>Four rows checked by hand</h2>
<div class="eu-scroll"><table class="eu-table"><thead><tr><th scope="col">Package</th><th scope="col">VNR</th><th scope="col">Result</th><th scope="col">Why</th></tr></thead><tbody>{check_rows}</tbody></table></div>
<p class="note">Tests in the repository check the route rule on these four cases.</p></section>
<section id="limits"><h2>Known limits</h2><ul class="steps">
<li>Fimea’s shortage file has no history, and its dates are estimates. Our history starts when we first saved the file; it is made of captures, not daily readings.</li>
<li>A package that leaves the file is “last seen” on the date of the last capture. That is not proof that supply returned.</li>
<li>A notice that Fimea edits (a changed start, end or notification date) shows in the file as a new notice. We count a notice that was edited, or that was missing from some captures and came back, as one shortage. A gap between captures is unknown time, not a new start. The length we give is “days between captures”: from the first to the last capture that listed the shortage.</li>
<li>The register describes today. We join old notices to today’s register, so a product that changed ATC code or route since then is shown as it is today.</li>
<li>The EU list names a substance and routes, not dosage forms or strengths. A match says that the substance and route are on the list, not that this exact product is one the EU list is about.</li>
<li>Combination products are matched by their own ATC code, and the list substance must be among their ingredients. The other ingredients are not checked against the list.</li>
<li>Shortages of products without a VNR are not in Fimea’s file, so they are not here.</li>
<li>The EU list changes. We keep version {E(meta['version'])} until we check and update it.</li>
<li>The match and the alerts are facts from public files. They give no advice, no risk score and no forecast. They do not name alternatives.</li>
<li>These pages are in English only.</li></ul></section>
<section id="alerts"><h2>Alerts</h2><p>The alert feeds list new shortages of packages with an exact match: the first capture that lists the shortage, with its VNR, ATC code, company and dates, and whether Fimea marks it ongoing or not yet started. Each shortage has one entry with a fixed id; an edited notice or one that returns after a missing capture is not a new alert. The daily build writes the feeds. Shortages already on the list when the archive started, or already listed for the same VNR in the capture before, are not new.</p>{downloads()}</section>
</div></div>'''
    return document('critical', body, meta=meta_for(FILE['methods'], 'How the critical medicines match works | Shortage Radar',
                    'Sources, licences, the match rule and the limits of the critical medicines page.'))


def render_critical(data):
    """{file: html} for the critical medicines page, the methods page and one page for each code on the EU list."""
    out = {FILE['critical']: critical_page(data), FILE['methods']: methods_page(data)}
    for code, row in data['eu']['rows'].items():
        out[code_file(code)] = code_page(code, row, data)
    return out


def sitemap_urls():
    return [SITE_URL + FILE['critical'], SITE_URL + FILE['methods']]
