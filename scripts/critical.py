"""Critical medicines in Finland: join the Fimea shortage file to the EU Union list of critical medicines.

Published facts only. A shortage package (VNR) is matched to the EU list by its ATC level 5 code, and then by route:

- `exact`: the ATC code is on the list and one of the package's routes (Fimea `Antoreitti`) fits a route of that list row.
- `route-mismatch`: the ATC code is on the list, but no route of the package fits. When Fimea gives no usable route the note
  says "route unclear"; the match type is not guessed in the package's favour.
- `unmatched`: the VNR is not in the Fimea register, so its ATC code is not known.

Fimea's own flag `EUKriittinenValmiste` is only a cross-check: where it disagrees, the note says so.
"""
import csv
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from statistics import median
from xml.sax.saxutils import escape

from changes import date_text

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'data/critical'
TYPES = ('exact', 'route-mismatch', 'ingredient-mismatch', 'unmatched')
ORDER = {'exact': 0, 'route-mismatch': 1, 'ingredient-mismatch': 2, 'unmatched': 3, 'flag-only': 4}
STATUS_NAMES = {'ongoing': 'Ongoing', 'upcoming': 'Starts later'}
TYPE_NAMES = {'exact': 'Exact match', 'route-mismatch': 'Route does not fit', 'unmatched': 'Not in the register', 'ingredient-mismatch': 'Ingredient not confirmed'}
EMA_PAGE = 'https://www.ema.europa.eu/en/human-regulatory-overview/post-authorisation/medicine-shortages-availability-issues/availability-medicines-during-crises/union-list-critical-medicines'
CC_BY = 'https://creativecommons.org/licenses/by/4.0/'
# Fields of a captured notice that the history keeps.
EVENT_KEYS = ('NordicArticleNumber', 'Valid', 'UnavailableFrom', 'EndingDate', 'DateOfTheNotification', 'Company', 'first_seen', 'last_seen', 'removed_on', 'listed_at_first_capture')


def load_eu_list(folder=FOLDER):
    """{'meta': {...}, 'rows': {atc: row}}; the pinned list copy with the sheet row of every entry."""
    meta = json.loads((folder / 'eu-list.json').read_text(encoding='utf-8'))
    with (folder / 'eu-list.csv').open(encoding='utf-8', newline='') as f:
        rows = {r['atc']: {'atc': r['atc'], 'description': r['description'], 'route': r['route'], 'included': r['date_of_inclusion'], 'row': int(r['source_row'])} for r in csv.DictReader(f)}
    return {'meta': meta, 'rows': rows}


def load_routes(folder=FOLDER):
    return json.loads((folder / 'routes.json').read_text(encoding='utf-8'))


def load_forms(folder=FOLDER):
    with (folder / 'forms.csv').open(encoding='utf-8', newline='') as f:
        return {r['id']: r['name_en'] for r in csv.DictReader(f)}


def load_ingredient_rules(folder=FOLDER):
    return json.loads((folder / 'ingredients.json').read_text(encoding='utf-8'))['overrides']


def _norm(text, brackets=False):
    """Lower case, hyphens as spaces, spaces collapsed; with `brackets`, text in brackets (a comment on a list entry) is removed."""
    text = text.casefold().replace('-', ' ')
    while brackets and '(' in text and ')' in text and text.index('(') < text.index(')'):
        text = text[:text.index('(')] + ' ' + text[text.index(')') + 1:]
    return ' '.join(text.split())


def _word_start(fragment, text):
    """Does `fragment` occur in `text` at the start of a word? "adrenaline" is not found in "noradrenaline"."""
    i = text.find(fragment)
    while i >= 0:
        if i == 0 or not text[i - 1].isalpha():
            return True
        i = text.find(fragment, i + 1)
    return False


def ingredient_fit(description, substances, rules=None):
    """Is the EU list substance among the product's active ingredients? Extra ingredients are allowed (combinations).

    By default every substance the list entry names ("PIPERACILLIN, TAZOBACTAM" names two) must be an active ingredient
    of the product, as the same name or as the start of its name ("Ipratropium bromide" for IPRATROPIUM). `rules`
    (ingredients.json) holds the entries the register names differently; for those, each group of fragments needs one
    found at the start of a word in an ingredient name. A product with no ingredients given cannot be confirmed.
    """
    names = [_norm(x) for x in substances if x]
    if not names:
        return False
    key = _norm(description, True)
    if rules and key in rules:
        return all(any(_word_start(_norm(f), n) for f in group for n in names) for group in rules[key])
    parts = [_norm(x, True) for x in description.split(',') if _norm(x, True)]
    return all(any(n == p or n.startswith(p + ' ') or n.startswith(p + ',') for n in names) for p in parts)


def list_routes(text):
    return [x.strip() for x in text.split(',') if x.strip()]


def route_fit(product_routes, list_route, table):
    """Does one of the package's Fimea routes fit a route of the EU list row? Returns (status, labels).

    `product_routes` is a list of (Fimea route id, Finnish text); `table` is the routes.json content.
    status is `fits`, `no` or `unclear`; `unclear` when the package has no route, or only routes that
    say nothing or that the table does not know. No keyword rules: only the table decides.
    """
    wanted = set(list_routes(list_route))
    known, fits = [], False
    for rid, _ in product_routes:
        entry = table['routes'].get(rid)
        if entry is None:
            continue
        known.append(entry['en'])
        if wanted & set(entry['eu']) or ('parenteral use' in wanted and entry['parenteral']):
            fits = True
    if fits:
        return 'fits', known
    return ('no' if known else 'unclear'), known


def note_for(match_type, status, flag, record):
    """The note shown with a match, in plain words."""
    parts = []
    if match_type == 'unmatched':
        return 'This VNR is not in the Fimea register, so its ATC code and route are not known.'
    if match_type == 'ingredient-mismatch':
        have = ', '.join(record['substance_list']) or 'none given'
        parts.append(f"The ATC code is on the list, but the active ingredient is not confirmed. List substance: {record['list_description'].title()}. Product ingredients: {have}.")
    elif match_type == 'exact':
        parts.append('The ATC code and the active ingredient are on the list and the route fits.')
    elif status == 'unclear':
        parts.append('The ATC code is on the list. Route unclear: Fimea gives no usable route for this product, so no route match is made.')
    else:
        parts.append(f"The ATC code is on the list, but the route does not fit. Product route: {', '.join(record['product_routes'])}. List route: {record['list_route']}.")
    if flag == '0':
        parts.append('Fimea does not flag this product as EU-critical; the ATC code, ingredient and route match the list.' if match_type == 'exact'
                     else 'Fimea does not flag this product as EU-critical.')
    elif flag == '1' and match_type != 'exact':
        parts.append('Fimea flags this product as EU-critical.')
    return ' '.join(parts)


def classify(vnr, product, detail, eu, table, forms, rules=None):
    """One match record for a VNR, or None when the VNR is in the register but its ATC code is not on the list and Fimea does not flag it.

    The ATC code is checked first, then the active ingredient (`ingredient-mismatch` when the list substance is not among the
    ingredients, or none are given), then the route. Packages that Fimea flags as EU-critical although their ATC code is not
    on the list get the type `flag-only`; they are kept out of the counts and shown apart.
    """
    if product is None:
        return {'vnr': vnr, 'match_type': 'unmatched', 'atc': '', 'name': '', 'strength': '', 'form': '', 'form_en': '', 'substances': '', 'pack': '', 'product_routes': [],
                'fimea_flag': '', 'list_row': None, 'list_route': '', 'note': note_for('unmatched', None, None, {})}
    flag = detail.get('eu_flag', '')
    row = eu['rows'].get(product.get('atc', ''))
    labels = [table['routes'][rid]['en'] for rid, _ in detail.get('routes', []) if rid in table['routes']]
    base = {'vnr': vnr, 'atc': product.get('atc', ''), 'name': product.get('name', ''), 'strength': product.get('strength', ''), 'form': product.get('form', ''),
            'form_en': forms.get(detail.get('form_id', ''), ''), 'substances': product.get('substances', ''), 'pack': product.get('pack', ''),
            'product_routes': labels, 'fimea_flag': flag}
    if row is None:
        if flag != '1':
            return None
        return dict(base, match_type='flag-only', list_row=None, list_route='', note='Fimea flags this product as EU-critical, but its ATC code is not on the EU list.')
    status, _ = route_fit(detail.get('routes', []), row['route'], table)
    substances = detail.get('substances') or [x for x in product.get('substances', '').split(', ') if x]
    if not ingredient_fit(row['description'], substances, rules):
        match_type = 'ingredient-mismatch'
    else:
        match_type = 'exact' if status == 'fits' else 'route-mismatch'
    record = dict(base, substance_list=substances, match_type=match_type, route_status={'fits': 'fits', 'no': 'does not fit', 'unclear': 'unclear'}[status], list_row=row['row'], list_route=row['route'], list_description=row['description'])
    record['note'] = note_for(match_type, status, flag, record)
    return record


def match_all(events, products, details, eu, table, forms, rules=None):
    """{vnr: record} for every VNR of the events (current or gone) that is on the list, flagged by Fimea, or not in the register."""
    out = {}
    for vnr in sorted({e['NordicArticleNumber'] for e in events}):
        record = classify(vnr, products.get(vnr), details.get(vnr, {}), eu, table, forms, rules)
        if record:
            out[vnr] = record
    return out


def current_rows(events, matches):
    """One row per current shortage VNR that has a match record; the latest notice of the VNR supplies the dates."""
    latest = {}
    for e in events:
        if e['removed_on'] is None and e['NordicArticleNumber'] in matches:
            old = latest.get(e['NordicArticleNumber'])
            if old is None or (e['DateOfTheNotification'], e['UnavailableFrom']) > (old['DateOfTheNotification'], old['UnavailableFrom']):
                latest[e['NordicArticleNumber']] = e
    rows = []
    for vnr, e in latest.items():
        # Fimea's Voimassa: K = ongoing (Kyllä), E = not started yet (Ei). Upcoming notices are not counted as current shortages.
        rows.append(dict(matches[vnr], company=e['Company'], start=e['UnavailableFrom'], end=e['EndingDate'], notified=e['DateOfTheNotification'], first_seen=e['first_seen'],
                         status='ongoing' if e['Valid'] == 'K' else 'upcoming'))
    return sorted(rows, key=lambda r: (r['status'] != 'ongoing', ORDER[r['match_type']], r['atc'], r['name'], r['vnr']))


def counts(rows):
    """{'ongoing': {type: n}, 'upcoming': {type: n}, 'disagree': n}: ongoing (Voimassa K) and not yet started (E) are counted apart."""
    out = {status: dict.fromkeys(TYPES + ('flag-only',), 0) for status in STATUS_NAMES}
    for r in rows:
        out[r['status']][r['match_type']] += 1
    out['disagree'] = sum(1 for r in rows if r['status'] == 'ongoing' and r['match_type'] in ('exact', 'route-mismatch') and r['fimea_flag'] in ('0', '1')
                          and (r['fimea_flag'] == '1') != (r['match_type'] == 'exact'))
    return out


def credit(meta, sources=None):
    """The credit that goes with every copy of the data (CSV, JSON, feeds): EMA for the list, Fimea with file names, file
    modification times (the HTTP Last-Modified of the files; the publisher gives no release times) and the CC BY 4.0 link,
    and the note that Shortage Radar changed the data."""
    sources = sources or {}
    modified = lambda key: f"file modification time {sources[key]} (HTTP Last-Modified)" if sources.get(key) else 'file modification time not recorded'
    return (f"EU list: European Medicines Agency (EMA), Union list of critical medicines, version {meta['version']} ({meta['reference']}), {meta['published']}, {EMA_PAGE}. "
            f"EMA is the source of the list and is acknowledged as such. "
            f"Shortages: Finnish Medicines Agency Fimea, file Shortages.txt (also published as Saatavuushairiot.txt), {modified('shortages_last_modified')}. "
            f"Register: Fimea, file Perusrekisteri2026.xml, {modified('register_last_modified')}. "
            f"Fimea data is licensed under CC BY 4.0 ({CC_BY}). Shortage Radar selected, joined and changed the data; neither EMA nor Fimea endorses the result.")


def csv_rows(rows, meta, sources=None):
    """CSV lines for the download: every current match, with the list version, the list row and the source credit."""
    header = ['VNR', 'ATC', 'name', 'strength', 'form', 'active substances', 'company', 'status', 'start date', 'estimated end date', 'notification date', 'match type',
              'route status', 'product route', 'list route', 'list version', 'list row', 'Fimea EU-critical flag', 'note', 'source credit']
    yield header
    for r in rows:
        yield [r['vnr'], r['atc'], r.get('name', ''), r.get('strength', ''), r.get('form_en') or r.get('form', ''), r.get('substances', ''), r.get('company', ''), STATUS_NAMES[r['status']].lower(), r.get('start', ''), r.get('end', ''),
               r.get('notified', ''), r['match_type'], r.get('route_status', ''), '; '.join(r.get('product_routes', [])), r.get('list_route', ''), meta['version'],
               r['list_row'] if r.get('list_row') else '', {'0': 'no', '1': 'yes'}.get(r.get('fimea_flag', ''), ''), r['note'], credit(meta, sources)]


def json_data(rows, meta, source_metadata, snapshot_date):
    sources = {k: (source_metadata or {}).get(k) for k in ('shortages_last_modified', 'register_last_modified')}
    text = credit(meta, sources)
    return {'title': 'Critical medicines in Finland', 'snapshot_date': snapshot_date, 'list': {k: meta[k] for k in ('version', 'reference', 'published', 'source_url', 'retrieved', 'rows')},
            'counts': counts(rows), 'source_credit': text,
            'sources': {'ema': {'name': 'Union list of critical medicines', 'version': meta['version'], 'reference': meta['reference'], 'published': meta['published'], 'url': EMA_PAGE,
                                'credit': 'European Medicines Agency (EMA)'},
                        'fimea': {'licence': 'CC BY 4.0', 'licence_url': CC_BY, 'changed': 'Shortage Radar selected, joined and changed the data',
                                  'files': [{'name': 'Shortages.txt', 'also_published_as': 'Saatavuushairiot.txt', 'file_modified': sources['shortages_last_modified'], 'file_modified_is': 'HTTP Last-Modified'},
                                            {'name': 'Perusrekisteri2026.xml', 'file_modified': sources['register_last_modified'], 'file_modified_is': 'HTTP Last-Modified'}]}},
            'matches': [dict({k: v for k, v in r.items() if k not in ('first_seen', 'form')}, list_version=meta['version'], source_credit=text) for r in rows]}


def _days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def shortages(events, capture_days=()):
    """Join the notices of a VNR that are one shortage: the notice edited (a changed start, end or notification date shows
    up in the archive as a removal and a new notice in the same capture), and the notice that vanishes for some captures and
    returns. Returns merged shortages, each with `edits`, `unseen` (stretches between captures that did not list it, which
    are unknown) and `gaps` (spans between two captures further apart than MAX_GAP_DAYS, also unknown).

    A gap in the captures is not a new start and not an end: nothing is known about those days.
    """
    out = []
    by_vnr = {}
    for e in sorted(events, key=lambda e: (e['first_seen'], e['UnavailableFrom'])):
        by_vnr.setdefault(e['NordicArticleNumber'], []).append(e)
    days = sorted(capture_days)
    for chain in by_vnr.values():
        current = None
        for e in chain:
            identity = (e['UnavailableFrom'], e['DateOfTheNotification'], e['Company'])
            if current is not None:
                prev = current['_last']
                edited = prev.get('vnr_listed_at_removal') and prev['removed_on'] == e['first_seen']
                returned = prev['removed_on'] is not None and (prev['UnavailableFrom'], prev['DateOfTheNotification'], prev['Company']) == identity
                if edited or returned:
                    if edited:
                        current['edits'] += 1
                    else:
                        current['unseen'].append({'from': prev['last_seen'], 'to': e['first_seen']})
                    current.update({k: e[k] for k in ('Valid', 'UnavailableFrom', 'EndingDate', 'DateOfTheNotification', 'Company', 'last_seen', 'removed_on')}, _last=e)
                    continue
            current = {k: e[k] for k in EVENT_KEYS}
            current.update(_last=e, edits=0, unseen=[], first_seen_after=e['first_seen_after'], origin=(e['NordicArticleNumber'], *identity))
            out.append(current)
    for n in out:
        n.pop('_last')
        n['gaps'] = [{'from': a, 'to': b, 'days': _days(a, b)} for a, b in zip(days, days[1:]) if n['first_seen'] <= a and b <= n['last_seen'] and _days(a, b) > MAX_GAP_DAYS]
        n['days_between_captures'] = _days(n['first_seen'], n['last_seen'])
    return out


def history(events, matches, capture_days=()):
    """Per ATC code: the shortages of the archive for packages with that code, and what they show.

    The archive is made of captures, not daily observations, so a shortage has a first and a last capture that listed it,
    not an exact start or end. One that is no longer listed shows the date it was `last seen`. `days_between_captures`
    counts from the first to the last capture that listed it, so it is a lower bound that includes any unknown stretch;
    shortages already listed in the first capture of the archive have no known start and are left out of the lengths,
    and so are those with a gap in the captures inside them.
    """
    by_code = {}
    for n in shortages([e for e in events if matches.get(e['NordicArticleNumber'], {}).get('atc')], capture_days):
        m = matches[n['NordicArticleNumber']]
        n.update(match_type=m['match_type'], name=m['name'], strength=m['strength'])
        by_code.setdefault(m['atc'], []).append(n)
    out = {}
    for atc, notices in by_code.items():
        notices.sort(key=lambda n: (n['first_seen'], n['NordicArticleNumber']), reverse=True)
        measured = [n['days_between_captures'] for n in notices if n['removed_on'] and not n['listed_at_first_capture'] and not n['gaps'] and not n['unseen']]
        out[atc] = {'notices': notices, 'count': len(notices), 'listed_now': sum(1 for n in notices if n['removed_on'] is None),
                    'gone': sum(1 for n in notices if n['removed_on']), 'measured': len(measured),
                    'days_min': min(measured) if measured else None, 'days_median': median(measured) if measured else None, 'days_max': max(measured) if measured else None}
    return out


def new_alerts(events, matches, snapshots, since):
    """[(shortage, match)] for exact matches whose shortage first appeared in a capture after `since`: the alert feed, one for each shortage.

    A shortage listed in the first capture of the archive, or whose VNR was already listed in the capture before it, is not
    new. A notice that was edited, or that vanished and returned, is the same shortage and is not new again.
    """
    listed = {day: {r['NordicArticleNumber'] for r in rows} for day, rows in snapshots}
    out = []
    for n in shortages(events, [d for d, _ in snapshots]):
        m = matches.get(n['NordicArticleNumber'])
        if (m and m['match_type'] == 'exact' and n['first_seen'] > since and not n['listed_at_first_capture']
                and n['NordicArticleNumber'] not in listed.get(n['first_seen_after'], ())):
            out.append((n, m))
    out.sort(key=lambda x: (x[0]['first_seen'], x[1]['atc'], x[0]['NordicArticleNumber']), reverse=True)
    return out


SITE_URL = 'https://alejandrorenalias.github.io/shortage-radar/'
TAG_BASE = 'tag:alejandrorenalias.github.io,2026:shortage-radar/critical/'
ALERT_DAYS = 30
MAX_GAP_DAYS = 14  # captures further apart than this tell nothing about the days between them
ALERT_MAX = 100
FEED_TITLE = 'Critical medicines in Finland: new shortages'
FEED_SUBTITLE = 'New shortage notices in Fimea’s file for packages that match the EU Union list of critical medicines by ATC code and route.'


def _day_text(value):
    return date_text(value, 'en') or 'not given'


def alert_item(n, m, meta, sources=None):
    """One alert as plain facts: what appeared, when we first saw it, and the match.

    The id comes from the first notice of the shortage (VNR, start, notification date, company), so it does not change when the
    notice is edited or returns after missing from a capture.
    """
    name = ' '.join(x for x in (m['name'], m['strength']) if x) or f"VNR {n['NordicArticleNumber']}"
    upcoming = n['Valid'] != 'K'
    lines = [f"First seen in the capture of {_day_text(n['first_seen'])}." + (' Fimea lists it as not started yet (Voimassa E).' if upcoming else ' Fimea lists it as ongoing (Voimassa K).'),
             f"ATC code: {m['atc']} ({m['list_description']}). Match: exact (EU list version {meta['version']}, row {m['list_row']}).",
             f"Product route: {', '.join(m['product_routes']) or 'not given'}. List route: {m['list_route']}.",
             f"Reported start: {_day_text(n['UnavailableFrom'])}. Company’s estimated end: {_day_text(n['EndingDate'])}. Notified: {_day_text(n['DateOfTheNotification'])}.",
             f"Company: {n['Company']}. VNR: {n['NordicArticleNumber']}."]
    if m['fimea_flag'] == '0':
        lines.append('Fimea does not flag this product as EU-critical.')
    lines.append(credit(meta, sources))
    key = '|'.join(n['origin'])
    return {'id': f"{TAG_BASE}{n['NordicArticleNumber']}/{hashlib.sha1(key.encode('utf-8')).hexdigest()[:10]}",
            'title': f"New {'upcoming ' if upcoming else ''}shortage: {name} ({m['atc']})", 'url': f"{SITE_URL}critical-{m['atc']}.html", 'date': n['first_seen'],
            'text': '\n'.join(lines), 'atc': m['atc'], 'vnr': n['NordicArticleNumber']}


def alert_items(alerts, meta, sources=None):
    """Feed items, newest first, one for each id: a repeated id keeps its earliest entry."""
    seen, items = set(), []
    for n, m in alerts:
        item = alert_item(n, m, meta, sources)
        if item['id'] not in seen:
            seen.add(item['id'])
            items.append(item)
    return items[:ALERT_MAX]


def rss_feed(items, meta, latest, sources=None):
    def rfc822(day):
        return datetime.strptime(day, '%Y-%m-%d').strftime('%a, %d %b %Y 00:00:00 +0000')
    parts = ['<?xml version="1.0" encoding="utf-8"?>', '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>', f'<title>{escape(FEED_TITLE)}</title>',
             f'<link>{SITE_URL}critical.html</link>', f'<description>{escape(FEED_SUBTITLE)}</description>', '<language>en</language>', f'<lastBuildDate>{rfc822(latest)}</lastBuildDate>',
             f'<atom:link href="{SITE_URL}critical-feed.xml" rel="self" type="application/rss+xml"/>', f'<copyright>{escape(credit(meta, sources))}</copyright>']
    for i in items:
        parts.append(f'<item><title>{escape(i["title"])}</title><link>{i["url"]}</link><guid isPermaLink="false">{i["id"]}</guid><pubDate>{rfc822(i["date"])}</pubDate>'
                     f'<category>{i["atc"]}</category><description>{escape(i["text"])}</description></item>')
    parts.append('</channel></rss>')
    return '\n'.join(parts) + '\n'


def json_feed(items, meta, sources=None):
    return json.dumps({'version': 'https://jsonfeed.org/version/1.1', 'title': FEED_TITLE, 'description': FEED_SUBTITLE, 'language': 'en', 'home_page_url': SITE_URL + 'critical.html',
                       'feed_url': SITE_URL + 'critical-feed.json', 'authors': [{'name': 'Shortage Radar', 'url': SITE_URL}], '_credit': credit(meta, sources),
                       'items': [{'id': i['id'], 'url': i['url'], 'title': i['title'], 'content_text': i['text'], 'date_published': i['date'] + 'T00:00:00Z', 'tags': [i['atc'], 'exact']} for i in items]},
                      ensure_ascii=False, indent=1) + '\n'


def write_outputs(site, rows, meta, source_metadata, snapshot_date, alerts):
    """Write the downloads and the alert feeds into the site folder."""
    with (site / 'critical.csv').open('w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerows(csv_rows(rows, meta, (source_metadata or {})))
    (site / 'critical.json').write_text(json.dumps(json_data(rows, meta, source_metadata, snapshot_date), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    sources = {k: (source_metadata or {}).get(k) for k in ('shortages_last_modified', 'register_last_modified')}
    items = alert_items(alerts, meta, sources)
    (site / 'critical-feed.xml').write_text(rss_feed(items, meta, snapshot_date, sources), encoding='utf-8', newline='\n')
    (site / 'critical-feed.json').write_text(json_feed(items, meta, sources), encoding='utf-8', newline='\n')
