"""Pages for "Critical medicines in Finland": the match page, the methods page and one page for every code on the EU list.

The pages are plain HTML written at build time, so they work without scripts; `site/critical.js` adds the filter and the language-dependent attributes.
Every text is in English and Finnish (the Finnish is a draft), see scripts/critical_copy.py. Facts only: no advice, no score, no forecast.
"""
from html import escape

import critical_charts as charts
from critical import STATUS_NAMES, TYPE_NAMES, TYPES, credit, load_routes
from critical_copy import STATUS_NAMES_FI, TYPE_NAMES_FI, Raw, bi, both, day, days, num, plain, swap, swap_attr, t
from gaps import MAX_GAP_DAYS
from pages import IMPACT_NAMES, SITE_URL, document

E = lambda value: escape(str(value if value is not None else ''), quote=True)
FIMEA_LICENCE = 'https://fimea.fi/en/about_us/open-data'
EU_TITLE = plain('title', 0)
EMA_NOTICE = 'https://www.ema.europa.eu/en/about-us/legal-notice'
EMA_LIST = 'https://www.ema.europa.eu/en/human-regulatory-overview/post-authorisation/medicine-shortages-availability-issues/availability-medicines-during-crises/union-list-critical-medicines'
# The two site labels that the explanation names: the English ones come from pages.py, the Finnish ones are the impact chips of site/i18n.js (a test keeps them equal).
IMPACT = {'substitute': (IMPACT_NAMES['substitute'], plain('impact.substitute', 1)), 'no_alternative': (IMPACT_NAMES['no_alternative'], plain('impact.no_alternative', 1))}
# Fimea's route names in Finnish for the English route glosses of the routes table (the first entry of a gloss wins).
ROUTE_FI = {}
for _entry in load_routes()['routes'].values():
    ROUTE_FI.setdefault(_entry['en'], _entry['fi'][:1].lower() + _entry['fi'][1:])
ROUTE_FI.update({'route not relevant': 'antoreitti ei oleellinen', 'on the skin or a surface': 'iholle tai pinnalle'})
FILE = {'critical': 'critical.html', 'methods': 'critical-methods.html'}
TYPE_EXPLAINED = {k: f'type.{k}' for k in TYPES}


def code_file(atc):
    return f'critical-{atc}.html'


def meta_for(file, title, description, script='critical.js'):
    return {'file': file, 'nav': None, 'title': title, 'description': description, 'form_action': "'none'", 'script': script}


def titles(en, fi, desc_en, desc_fi):
    """The page title and description in both languages, for site/critical.js (the document title is not part of the page body)."""
    return f' data-title-en="{E(en)}" data-title-fi="{E(fi)}" data-desc-en="{E(desc_en)}" data-desc-fi="{E(desc_fi)}"'


def bday(value):
    en, fi = day(value)
    return bi(E(en), E(fi))


def chip(match_type):
    return f'<span class="eu-chip eu-{match_type}">{bi(E(TYPE_NAMES.get(match_type, "Flagged by Fimea only")), E(TYPE_NAMES_FI[match_type]))}</span>'


def explained():
    return t('explained', substitute=IMPACT['substitute'], no_alternative=IMPACT['no_alternative'])


def name_cell(r):
    name = ' '.join(x for x in (r.get('name'), r.get('strength')) if x) or f"VNR {r['vnr']}"
    sub = r.get('substances') or ''
    form_en, form_fi = r.get('form_en') or r.get('form') or '', r.get('form') or r.get('form_en') or ''
    detail = both(', '.join(x for x in (sub, form_en) if x), ', '.join(x for x in (sub, form_fi) if x))
    return f'<strong>{E(name)}</strong>' + (f'<span class="note">{detail}</span>' if detail else '')


def status_cell(r):
    """Fimea's Voimassa: K is ongoing, E has not started yet; the start date shows when."""
    return f'<span>{t("row.ongoing" if r["status"] == "ongoing" else "row.later", date=day(r["start"]))}</span>'


def note_text(r, index):
    """The note of a row in one language (0 English, 1 Finnish); the same rules as `note_for` in scripts/critical.py (a test keeps the English text equal to it)."""
    match_type, flag = r['match_type'], r.get('fimea_flag')
    if match_type in ('unmatched', 'flag-only'):
        return plain('note.unmatched' if match_type == 'unmatched' else 'note.flag-only', index)
    if match_type == 'ingredient-mismatch':
        parts = [plain('note.ingredient-mismatch', index, list=r['list_description'].title(), have=', '.join(r['substance_list']) or plain('note.none_given', index))]
    elif match_type == 'exact':
        parts = [plain('note.exact', index)]
    elif r.get('route_status') == 'unclear':
        parts = [plain('note.unclear', index)]
    else:
        routes = [x if index == 0 else ROUTE_FI.get(x, x) for x in r['product_routes']]
        parts = [plain('note.route-mismatch', index, product=', '.join(routes), list=r['list_route'])]
    if flag == '0':
        parts.append(plain('note.flag0.exact' if match_type == 'exact' else 'note.flag0', index))
    elif flag == '1' and match_type != 'exact':
        parts.append(plain('note.flag1', index))
    return ' '.join(parts)


def row_note(r):
    """The note of a row in both languages; the English one is the note critical.py wrote."""
    return both(r['note'], note_text(r, 1))


def routes_text(r):
    en = list(r.get('product_routes') or [])
    return both(', '.join(en) or plain('row.not_given', 0), ', '.join(ROUTE_FI.get(x, x) for x in en) or plain('row.not_given', 1))


def notice_row(r, words=''):
    atc = f'<a href="{code_file(r["atc"])}">{E(r["atc"])}</a>' if r.get('atc') and r['match_type'] != 'flag-only' else E(r.get('atc') or '—')
    text = ' '.join(str(r.get(k, '')) for k in ('vnr', 'atc', 'name', 'substances', 'company', 'list_description')).casefold()
    route = (f'<dt>{t("row.route")}</dt><dd>{t("row.not_known")}</dd>' if r['match_type'] == 'unmatched'
             else f'<dt>{t("row.product_route")}</dt><dd>{routes_text(r)}</dd><dt>{t("row.list_route")}</dt><dd>{E(r.get("list_route") or "—")}</dd>')
    tag = '' if r['match_type'] == 'unmatched' else f'<span class="eu-route-line">{charts.route_tag(r.get("product_routes"), routes_text(r))}</span>'
    more = (f'<details class="eu-fold eu-row-more"><summary>{t("row.details")}</summary><p class="note">{row_note(r)}</p><dl class="eu-facts"><dt>{t("row.company")}</dt><dd>{E(r.get("company", ""))}</dd>'
            f'<dt class="eu-atc-fact">{t("th.atc")}</dt><dd class="eu-atc-fact">{atc}</dd><dt>{t("row.start")}</dt><dd>{bday(r["start"])}</dd>{route}<dt>{t("row.vnr")}</dt><dd>{E(r["vnr"])}</dd></dl></details>')
    return (f'<tr data-type="{E(r["match_type"])}" data-status="{r["status"]}" data-text="{E(text)}" data-fi="{E(words)}"><td data-label="Medicine">{name_cell(r)}{tag}{more}</td>'
            f'<td data-label="ATC code" class="eu-col-atc">{atc}</td><td data-label="Match">{chip(r["match_type"])}</td><td data-label="Status">{status_cell(r)}</td><td data-label="Estimated end"><span class="eu-end-label">{t("th.end")}</span> <span class="eu-end">{bday(r.get("end"))}</span></td></tr>')


def downloads():
    return (f'<ul class="links"><li><a href="critical.csv">{t("download.csv")}</a></li><li><a href="critical.json">{t("download.json")}</a></li>'
            f'<li><a href="critical-feed.xml">{t("download.rss")}</a></li><li><a href="critical-feed.json">{t("download.feed")}</a></li></ul>')


def credit_text(meta, source_metadata):
    """The legal source credit that ships with the downloads; it stays in English (lang="en") in both views."""
    return Raw(f'<span lang="en">{E(credit(meta, source_metadata))}</span>')


def source_block(meta, snapshot_date, source_metadata):
    return (f'<p class="note">{t("source.short")}</p>'
            f'<details class="eu-fold"><summary>{t("source.full")}</summary><p class="note">{credit_text(meta, source_metadata)}</p>'
            f'<p class="note l-fi-only">{t("source.english")}</p>'
            f'<p class="note">{t("source.snapshot", date=day(snapshot_date))}</p></details>')


INFO_ICON = '<svg class="uicon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>'


def info(label, text):
    """A small "i" that opens a short note in place; it works without scripts and with the keyboard. `label` is a pair (English, Finnish)."""
    return f'<details class="eu-info"><summary{swap_attr("aria-label", "tile.info", label=label)}>{INFO_ICON}</summary><div class="eu-info-text">{text}</div></details>'


def tile(number, label, sub='', small=False, more=''):
    """A key number with its short label (a pair). `sub` is a short line shown under it; `more` is a longer explanation that sits behind the "i"."""
    return (f'<li class="eu-tile"><span class="eu-num{" eu-num-date" if small else ""}">{number}</span><span class="eu-tile-label">{bi(E(label[0]), E(label[1]))}</span>'
            + (info(label, more) if more else '') + (f'<span class="eu-tile-sub">{sub}</span>' if sub else '') + '</li>')


def tile_more(kind, ongoing, upcoming, checked):
    """The note behind the "i" of one match box."""
    text = t(TYPE_EXPLAINED[kind])
    if kind == 'exact':
        text += t('tile.exact', checked=(plain('n.ongoing' if checked == 1 else 'n.ongoing.many', 0, n=f'{checked:,}'), ''), n=num(checked), exact=num(ongoing['exact']))
        if upcoming['exact']:
            text += t('tile.later', n=num(upcoming['exact']))
    return text


def split_text(counts_by_type):
    return ('; '.join(f'{n:,} {TYPE_NAMES[k].lower()}' for k, n in counts_by_type.items() if n),
            '; '.join(f'{n:,} {TYPE_NAMES_FI[k].lower()}' for k, n in counts_by_type.items() if n))


def critical_page(data):
    meta, rows, counts = data['eu']['meta'], data['rows'], data['counts']
    ongoing, upcoming = counts['ongoing'], counts['upcoming']
    checked_ongoing, checked_upcoming = sum(ongoing[k] for k in TYPES), sum(upcoming[k] for k in TYPES)
    tiles = ''.join(tile(f'{ongoing[k]:,}', (TYPE_NAMES[k], TYPE_NAMES_FI[k]), more=tile_more(k, ongoing, upcoming, checked_ongoing)) for k in TYPES)
    flag = counts['disagree']
    flag_only = ongoing['flag-only'] + upcoming['flag-only']
    flag_pkg = (plain('n.ongoing.gen' if flag == 1 else 'n.ongoing.gen.many', 0, n=f'{flag:,}'), plain('n.ongoing.gen', 1, n=num(flag)[1]))
    more = (plain('flag.more', 0, n=f'{flag_only:,}'), plain('flag.more', 1, n=num(flag_only)[1])) if flag_only else ''
    flag_line = '<p>' + t('flag', pkg=flag_pkg, more=more) + '</p>'
    if checked_upcoming:
        pkg = (plain('n.checked' if checked_upcoming == 1 else 'n.checked.many', 0, n=f'{checked_upcoming:,}'), plain('n.checked', 1, n=num(checked_upcoming)[1]))
        later_line = '<p>' + t('later.some', pkg=pkg, has=('has' if checked_upcoming == 1 else 'have', ''), split=split_text(upcoming)) + '</p>'
    else:
        later_line = '<p>' + t('later.none') + '</p>'
    notes = (f'<details class="eu-fold eu-notes"><summary>{t("details.list")}</summary>'
             f'<p>{explained()}</p><p class="note">{t("list.version", version=meta["version"])}</p>'
             f'<p>{t("notes.advice")}</p>'
             f'{later_line}{flag_line}'
             f'<p>{t("notes.end")}</p>'
             f'<p>{t("notes.data", iso=data["snapshot_date"], date=day(data["snapshot_date"]))}</p>'
             f'{source_block(meta, data["snapshot_date"], data["source_metadata"])}'
             f'<p class="note">{t("notes.links", methods=FILE["methods"])}</p></details>')
    words = data.get('substance_fi') or {}
    body_rows = ''.join(notice_row(r, words.get(r['vnr']) or '') for r in rows) or f'<tr><td colspan="5">{t("empty.list")}</td></tr>'
    codes = ''.join(
        f'<li><a href="{code_file(a)}"><span class="eu-code">{E(a)}</span> {E(row["description"].title())}</a>'
        + (f' <span class="note">{t("codes.archive", n=num(data["history"][a]["count"]))}</span>' if a in data['history'] else '') + '</li>'
        for a, row in sorted(data['eu']['rows'].items()))
    option = lambda value, key: f'<option value="{value}"{swap(key)}>{E(plain(key, 0))}</option>'
    type_options = ''.join(f'<option value="{k}" data-en="{E(TYPE_NAMES[k])}" data-fi="{E(TYPE_NAMES_FI[k])}">{E(TYPE_NAMES[k])}</option>' for k in TYPES)
    body = f"""<div class="wrap page-head eu-head"{titles(f'{EU_TITLE} | {plain("site", 0)}', f'{plain("title", 1)} | {plain("site", 1)}', plain('meta.list', 0), plain('meta.list', 1))}><div><h1>{t('title')}</h1>
<p class="lead">{t('lead.list')}</p>
<p class="note eu-advice-short">{t('advice.short')}</p></div>{charts.hero_art()}</div>
<section class="wrap" aria-labelledby="eu-counts-title"><h2 id="eu-counts-title" class="eu-counts-title">{t('counts.title')}</h2>
<ul class="eu-tiles">{tiles}</ul>
{notes}
<details class="eu-fold eu-charts-fold" id="eu-charts-fold" open><summary>{t('charts.fold')}</summary><div class="eu-charts">{charts.group_bars(rows)}{charts.route_row(rows)}</div></details></section>
<section class="wrap eu-list" aria-labelledby="eu-table-title"><h2 id="eu-table-title" tabindex="-1">{t('table.title')}</h2>
<form class="eu-filter needs-js" id="eu-filter" autocomplete="off"><div class="eu-field eu-search"><label for="eu-q">{t('filter.search')}</label><input id="eu-q" type="search" autocomplete="off" maxlength="100"{swap_attr('placeholder', 'filter.placeholder')}></div>
<div class="eu-field"><label for="eu-type">{t('filter.match')}</label><select id="eu-type">{option('', 'filter.all')}{type_options}</select></div>
<div class="eu-field"><label for="eu-status">{t('filter.status')}</label><select id="eu-status">{option('', 'filter.status.all')}{option('ongoing', 'status.ongoing')}{option('upcoming', 'status.upcoming')}</select></div>
<p class="note" id="eu-shown" role="status" aria-live="polite"></p></form>
<div class="eu-scroll"><table class="eu-table"><thead><tr><th scope="col">{t('th.medicine')}</th><th scope="col">{t('th.atc')}</th><th scope="col">{t('th.match')}</th><th scope="col">{t('th.status')}</th><th scope="col">{t('th.end')}</th></tr></thead><tbody id="eu-body">{body_rows}</tbody></table></div>
<nav class="eu-pager needs-js" id="eu-pager"{swap_attr('aria-label', 'pager.label')} hidden></nav></section>
<section class="wrap eu-more" aria-labelledby="eu-dl-title"><h2 id="eu-dl-title">{t('download.title')}</h2>{downloads()}
<details class="eu-fold"><summary>{t('codes.fold', n=len(data['eu']['rows']))}</summary><ul class="eu-codes">{codes}</ul></details></section>"""
    return document('critical', body, meta=meta_for(FILE['critical'], f'{EU_TITLE} | {plain("site", 0)}', plain('meta.list', 0)))


def timeline_item(n):
    seen = t('step.still') if n['removed_on'] is None else t('step.last', date=day(n['last_seen']))
    if n['listed_at_first_capture']:
        first = t('step.first.capture', date=day(n['first_seen']))
    elif n['start_unknown']:
        first = t('step.first.gap', date=day(n['first_seen']), n=n['start_gap_days'])
    else:
        first = t('step.first', date=day(n['first_seen']))
    notes = []
    if n['edits']:
        notes.append(t('step.edited', n=n['edits'], word=(plain('step.time' if n['edits'] == 1 else 'step.times', 0), plain('step.time' if n['edits'] == 1 else 'step.times', 1))))
    notes += [t('step.unseen', a=day(u['from']), b=day(u['to'])) for u in n['unseen']]
    unobserved = ''.join(f'<p class="note">{t("step.unobserved", a=day(g["from"]), b=day(g["to"]))}</p>' for g in n['gaps'])
    between = t('unknown') if (n['gaps'] or n['unseen']) else str(n['days_between_captures'])
    name = " ".join(x for x in (n["name"], n["strength"]) if x)
    return (f'<li class="eu-step"><div class="eu-step-head"><strong>{E(name)}</strong> {chip(n["match_type"])}</div>'
            f'<p class="eu-step-line">{first} · {seen}</p>{unobserved}'
            f'<details class="eu-fold"><summary>{t("row.details")}</summary><dl class="eu-facts"><dt>{t("dl.package")}</dt><dd>{t("step.package", vnr=n["NordicArticleNumber"], company=n["Company"])}</dd>'
            f'<dt>{t("row.start")}</dt><dd>{bday(n["UnavailableFrom"])}</dd><dt>{t("dl.between")}</dt><dd>{between}</dd></dl>'
            + ''.join(f'<p class="note">{x}</p>' for x in notes) + '</details></li>')


def history_block(code, h, archive_start, snapshot_date):
    if not h:
        return f'<p>{t("hist.none")}</p>'
    key = 'hist.shortage' if h['count'] == 1 else 'hist.shortages'
    lines = [f'<p>{t("hist.count", n=num(h["count"]), word=(plain(key, 0), plain(key, 1)), since=day(archive_start), now=num(h["listed_now"]), gone=num(h["gone"]))}</p>']
    if h['measured']:
        measured = '<p>' + t('hist.measured', m=num(h['measured']), min=days(h['days_min']), med=days(round(h['days_median'])), max=days(h['days_max'])) + '</p>'
    else:
        measured = f'<p>{t("hist.nomeasure")}</p>'
    lines.append(charts.timeline_strip(h['notices'], archive_start, snapshot_date))
    items = [timeline_item(n) for n in h['notices']]
    shown, rest = items[:8], items[8:]
    timeline = f'<ol class="eu-timeline">{"".join(shown)}</ol>'
    if rest:
        word = 'hist.earlier.one' if len(rest) == 1 else 'hist.earlier.many'
        timeline += f'<details class="eu-fold"><summary>{t("hist.earlier", n=num(len(rest)), word=(plain(word, 0), plain(word, 1)))}</summary><ol class="eu-timeline">{"".join(rest)}</ol></details>'
    lines.append(f'<p class="note">{t("hist.newest")}</p>')
    lines.append(timeline)
    lines.append(f'<details class="eu-fold"><summary>{t("hist.how")}</summary>{measured}<p class="note">{t("hist.how1", max=MAX_GAP_DAYS)}</p><p class="note">{t("hist.how2")}</p></details>')
    return ''.join(lines)


def summary_tiles(code, row, notices, h, snapshot_date):
    ongoing = sum(1 for r in notices if r['status'] == 'ongoing')
    later = len(notices) - ongoing
    pair = lambda key: (plain(key, 0), plain(key, 1))
    if notices:
        status = t('tile.ongoing', n=num(ongoing)) if ongoing else t('tile.noneongoing')
        sub = t('tile.startlater', n=num(later)) if later else ''
        dates = [r['notified'] for r in notices if r.get('notified')]
        last_date, last_sub = (max(dates) if dates else None), t('tile.last.sub')
    else:
        status, sub = t('tile.nomatch'), t('tile.nomatch.sub', date=day(snapshot_date))
        last_date, last_sub = max((n['last_seen'] for n in (h or {}).get('notices', []) if n.get('last_seen')), default=None), t('tile.last.seen')
    return ''.join((tile(E(row['description'].title()), pair('tile.substance'), t('tile.atcsub', code=code), True),
                    tile(status, pair('tile.status'), sub, small=not notices),
                    tile(bday(last_date) if last_date else t('tile.none'), pair('tile.last'), last_sub if last_date else t('tile.none.sub'))))


def code_page(code, row, data):
    meta = data['eu']['meta']
    notices = [r for r in data['rows'] if r.get('atc') == code]
    h = data['history'].get(code)
    current = ''.join(
        f'<li class="eu-card"><div class="eu-card-head"><div>{name_cell(r)}</div>{chip(r["match_type"])}</div><p class="eu-step-line">{bi(E(STATUS_NAMES[r["status"]]), E(STATUS_NAMES_FI[r["status"]]))} · {E(r["company"])} · {charts.route_tag(r["product_routes"], routes_text(r))}</p>'
        f'<details class="eu-fold"><summary>{t("row.details")}</summary><p class="note">{row_note(r)}</p>'
        f'<dl class="eu-facts"><dt>{t("row.start")}</dt><dd>{bday(r["start"])}</dd><dt>{t("dl.end")}</dt><dd>{bday(r["end"])}</dd>'
        f'<dt>{t("dl.notified")}</dt><dd>{bday(r["notified"])}</dd><dt>{t("row.vnr")}</dt><dd>{E(r["vnr"])}</dd><dt>{t("row.product_route")}</dt><dd>{routes_text(r)}</dd></dl></details></li>'
        for r in notices)
    current = f'<ul class="eu-cards">{current}</ul>' if current else f'<p>{t("nonotice", date=day(data["snapshot_date"]))}</p>'
    title = f'{row["description"].title()} ({code})'
    title_en = f'{title} | {plain("code.titlesuffix", 0)} | {plain("site", 0)}'
    head = titles(title_en, f'{title} | {plain("code.titlesuffix", 1)} | {plain("site", 1)}', plain('meta.code', 0, code=code), plain('meta.code', 1, code=code))
    body = f"""<div class="wrap page-head"{head}><p class="note"><a href="{FILE['critical']}">{t('back')}</a></p><h1>{E(title)}</h1>
<p class="lead">{t('lead.code', code=code, version=meta['version'])}</p>
<p class="note eu-advice-short">{t('advice.short')}</p></div>
<div class="wrap eu-code-page">
<ul class="eu-tiles">{summary_tiles(code, row, notices, h, data['snapshot_date'])}</ul>
<section aria-labelledby="h-now"><h2 id="h-now">{t('h.now')}</h2>{current}</section>
<section aria-labelledby="h-history"><h2 id="h-history">{t('h.history')}</h2>{history_block(code, h, data['archive_start'], data['snapshot_date'])}</section>
<section aria-labelledby="h-list"><h2 id="h-list" class="sr-only">{t('h.list')}</h2><details class="eu-fold"><summary>{t('h.list')}</summary>
<dl class="eu-facts"><dt>{t('list.atc')}</dt><dd>{E(code)}</dd><dt>{t('list.substance')}</dt><dd>{E(row['description'])}</dd><dt>{t('list.routes')}</dt><dd>{E(row['route'])}</dd>
<dt>{t('list.included')}</dt><dd>{bday(row['included'])}</dd><dt>{t('list.version.label')}</dt><dd>{E(meta['version'])} ({E(meta['reference'])}, {bday(meta['published'])})</dd><dt>{t('list.row')}</dt><dd>{row['row']}</dd></dl></details></section>
<section><details class="eu-fold eu-notes"><summary>{t('details.code')}</summary>
<p>{explained()}</p>
<p>{t('notes.advice.code', methods=FILE['methods'])}</p>
<p class="note">{t('source.short')}</p>
<details class="eu-fold"><summary>{t('source.full')}</summary><p class="note">{credit_text(meta, data['source_metadata'])}</p><p class="note l-fi-only">{t('source.english')}</p></details></details>{downloads()}</section></div>"""
    return document('critical', body, meta=meta_for(code_file(code), title_en, plain('meta.code', 0, code=code)))


def methods_page(data):
    meta = data['eu']['meta']
    checks = [('Desmopressin Sandoz', '416337', 'route-mismatch', 1), ('Desmopressin STADA', '448525', 'route-mismatch', 2), ('Desmopressin ratiopharm', '485073', 'route-mismatch', 3),
              ('Minirin', '022246', 'route-mismatch', 4), ('Minirin', '022288', 'route-mismatch', 5), ('Miochol-E', '019235', 'exact', 6)]
    type_name = lambda k: bi(E(TYPE_NAMES[k]), E(TYPE_NAMES_FI[k]))
    type_items = ''.join(f'<li><strong>{type_name(k)}.</strong> {t(TYPE_EXPLAINED[k])}</li>' for k in TYPES)
    check_rows = ''.join(f'<tr><td data-label="Package">{E(n)}</td><td data-label="VNR">{v}</td><td data-label="Result">{type_name(k)}</td><td data-label="Why">{t(f"m.check.{i}")}</td></tr>' for n, v, k, i in checks)
    register = (data['source_metadata'] or {}).get('register_file') or 'Perusrekisteri'
    li = lambda *keys, **f: ''.join(f'<li>{t(k, **f)}</li>' for k in keys)
    head = titles(f'{plain("methods.title", 0)} | {plain("site", 0)}', f'{plain("methods.title", 1)} | {plain("site", 1)}', plain('meta.methods', 0), plain('meta.methods', 1))
    body = f"""<div class="wrap page-head"{head}><p class="note"><a href="{FILE['critical']}">{t('back')}</a></p><h1>{t('methods.title')}</h1>
<p class="lead">{t('lead.methods')}</p>
<p class="note eu-advice-short">{t('advice.short')}</p></div>
<div class="wrap about-layout"><div class="prose">
<section id="critical"><h2>{t('m.critical.h')}</h2><p>{explained()}</p></section>
<section id="sources"><h2>{t('m.sources.h')}</h2><ul class="steps">
{li('m.src.eu', ema_list=Raw(EMA_LIST), version=meta['version'], reference=meta['reference'], published=day(meta['published']), rows=len(data['eu']['rows']))}
{li('m.src.shortage', licence=Raw(FIMEA_LICENCE))}
{li('m.src.register', register=register)}
{li('m.src.forms', 'm.src.archive')}</ul></section>
<section id="licences"><h2>{t('m.licences.h')}</h2>
<p>{t('m.lic.fimea')}</p>
<p>{t('m.lic.ema', notice=Raw(EMA_NOTICE))}</p>
<p>{t('m.lic.credit', credit=credit_text(meta, data['source_metadata']))}</p>
<p>{t('m.lic.code')}</p></section>
<section id="types"><h2>{t('m.types.h')}</h2><ul class="steps">{type_items}</ul></section>
<section id="rule"><h2>{t('m.rule.h')}</h2><ol class="steps">
{li('m.rule.atc', 'm.rule.ingredient', 'm.rule.route', 'm.rule.result', 'm.rule.ongoing', 'm.rule.unclear', 'm.rule.cross')}</ol></section>
<section id="checked"><h2>{t('m.checked.h')}</h2>
<div class="eu-scroll"><table class="eu-table"><thead><tr><th scope="col">{t('m.checked.th.package')}</th><th scope="col">{t('row.vnr')}</th><th scope="col">{t('m.checked.th.result')}</th><th scope="col">{t('m.checked.th.why')}</th></tr></thead><tbody>{check_rows}</tbody></table></div>
<p class="note">{t('m.checked.note')}</p></section>
<section id="limits"><h2>{t('m.limits.h')}</h2><ul class="steps">
{li('m.lim.1', 'm.lim.2')}{li('m.lim.3', 'm.lim.4', max=MAX_GAP_DAYS)}{li('m.lim.5', 'm.lim.6', 'm.lim.7', 'm.lim.8')}{li('m.lim.9', version=meta['version'])}{li('m.lim.10')}</ul></section>
<section id="alerts"><h2>{t('m.alerts.h')}</h2><p>{t('m.alerts', max=MAX_GAP_DAYS)}</p>{downloads()}</section>
</div></div>"""
    return document('critical', body, meta=meta_for(FILE['methods'], f'{plain("methods.title", 0)} | {plain("site", 0)}', plain('meta.methods', 0)))


def render_critical(data):
    """{file: html} for the critical medicines page, the methods page and one page for each code on the EU list."""
    out = {FILE['critical']: critical_page(data), FILE['methods']: methods_page(data)}
    for code, row in data['eu']['rows'].items():
        out[code_file(code)] = code_page(code, row, data)
    return out


def sitemap_urls():
    return [SITE_URL + FILE['critical'], SITE_URL + FILE['methods']]
