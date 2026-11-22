"""Weekly summary and Atom feeds built from the capture history."""
import hashlib
from datetime import date, datetime, timedelta
from xml.sax.saxutils import escape

from packs import name_with_strength, strength_label

SITE_URL = 'https://alejandrorenalias.github.io/shortage-radar/'
TAG_BASE = 'tag:alejandrorenalias.github.io,2026:shortage-radar/'
WEEK_DAYS = 7
# A comparison capture further back than this is no longer "this week".
MAX_WEEK_WINDOW_DAYS = 10
FEED_DAYS = 14
FEED_MAX_ENTRIES = 200
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

TEXT = {
    'en': {
        'lang': 'en', 'file': 'feed.xml', 'title': 'Shortage Radar — Finland: changes',
        'subtitle': 'Medicine shortages that appeared on or left the Fimea list in the last 14 days, and medicines that newly have no interchangeable product on the market.',
        'new': 'New on the list', 'left': 'Left the list', 'unknown': 'Unnamed package', 'company': 'Company',
        'since': 'Reported start', 'end': 'Estimated end', 'notified': 'Notification date', 'none': 'not given',
        'first_seen': lambda day, after: f'First seen in the capture of {day}' + (f' (not in the capture of {after})' if after else '') + '.',
        'last_seen': lambda last, day: f'Last listed in the capture of {last}; absent from the capture of {day}. Removal from the list is not proof that supply returned.',
        'critical': 'No interchangeable product on the market',
        'critical_when': lambda day, after: f'From the capture of {day} (not yet in the capture of {after}), no other package in this substitution group is on the market without a shortage.',
        'critical_advice': 'Talk to your pharmacist or doctor early. “On the market” comes from the register and is not a pharmacy stock check.',
        'listed': 'Packages on the shortage list',
    },
    'fi': {
        'lang': 'fi', 'file': 'feed-fi.xml', 'title': 'Saatavuustutka — Suomi: muutokset',
        'subtitle': 'Fimean listalle tulleet ja siltä poistuneet lääkkeiden saatavuushäiriöt viimeisen 14 päivän aikana sekä lääkkeet, joille ei enää ole vaihtokelpoista valmistetta kaupan.',
        'new': 'Uusi listalla', 'left': 'Poistui listalta', 'unknown': 'Nimetön pakkaus', 'company': 'Yritys',
        'since': 'Ilmoitettu alkamispäivä', 'end': 'Arvioitu päättymispäivä', 'notified': 'Ilmoituspäivä', 'none': 'ei ilmoitettu',
        'first_seen': lambda day, after: f'Havaittu ensimmäisen kerran tilannekuvassa {day}' + (f' (ei ollut tilannekuvassa {after})' if after else '') + '.',
        'last_seen': lambda last, day: f'Viimeksi listalla tilannekuvassa {last}; ei enää tilannekuvassa {day}. Listalta poistuminen ei todista, että lääkettä on taas saatavilla.',
        'critical': 'Ei vaihtokelpoista valmistetta kaupan',
        'critical_when': lambda day, after: f'Tilannekuvasta {day} alkaen (ei vielä tilannekuvassa {after}) tämän vaihtokelpoisuusryhmän muita pakkauksia ei ole kaupan ilman saatavuushäiriötä.',
        'critical_advice': 'Kysy apteekista tai lääkäriltä hyvissä ajoin. Tieto kaupan olosta tulee lääkerekisteristä, eikä se kerro apteekin varastosta.',
        'listed': 'Saatavuushäiriölistalla olevat pakkaukset',
    },
}


def date_text(value, lang):
    """Dates as the site shows them: 21 Nov 2026 in English, 21.11.2026 in Finnish."""
    if not value:
        return ''
    d = date.fromisoformat(value)
    return f'{d.day}.{d.month}.{d.year}' if lang == 'fi' else f'{d.day} {MONTHS[d.month - 1]} {d.year}'


def _day(value):
    return date.fromisoformat(value)


def _shift(day, days):
    return (_day(day) - timedelta(days=days)).isoformat()


def _replaced(snapshots):
    """Return the check that tells whether a package had another record listed on a given capture."""
    listed = {day: {r['NordicArticleNumber'] for r in rows} for day, rows in snapshots}
    return lambda vnr, day: day is not None and vnr in listed.get(day, ())


def _arrivals_and_exits(es, snapshots, since):
    """New and removed events after `since`. A package whose record was only replaced by a changed one is not counted."""
    listed = _replaced(snapshots)
    new = [e for e in es if e['first_seen'] > since and not e['listed_at_first_capture'] and not listed(e['NordicArticleNumber'], e['first_seen_after'])]
    left = [e for e in es if e['removed_on'] and e['removed_on'] > since and not e.get('vnr_listed_at_removal')]
    return new, left


def week_summary(es, snapshots, history):
    """Compare the latest capture with the newest capture at least a week older; None when no such capture is close enough."""
    latest = history[-1]
    cutoff = _shift(latest['date'], WEEK_DAYS)
    base = next((h for h in reversed(history) if h['date'] <= cutoff), None)
    if base is None or (_day(latest['date']) - _day(base['date'])).days > MAX_WEEK_WINDOW_DAYS:
        return None
    new, left = _arrivals_and_exits(es, snapshots, base['date'])
    return {'from': base['date'], 'to': latest['date'], 'days': (_day(latest['date']) - _day(base['date'])).days,
            'new': len(new), 'left': len(left), 'count_from': base['count'], 'count_to': latest['count']}


def _entry_text(e, lang, kind):
    t = TEXT[lang]
    pack = (e.get('pack_label') or {}).get(lang) or e.get('pack', '')
    name = name_with_strength(e.get('name'), e.get('strength'), lang, pack) if e.get('name') else f"VNR {e['NordicArticleNumber']}"
    d = lambda value: date_text(value, lang)
    when = t['first_seen'](d(e['first_seen']), d(e['first_seen_after'])) if kind == 'new' else t['last_seen'](d(e['last_seen']), d(e['removed_on']))
    lines = [when, f"{t['since']}: {d(e['UnavailableFrom']) or t['none']}", f"{t['end']}: {d(e['EndingDate']) or t['none']}", f"{t['notified']}: {d(e['DateOfTheNotification']) or t['none']}", f"{t['company']}: {e['Company']}", f"VNR: {e['NordicArticleNumber']}"]
    return f"{t[kind]}: {name}" + (f', {pack}' if pack else ''), '\n'.join(lines)


def _entry_id(e, kind):
    key = '|'.join([e['NordicArticleNumber'], e['UnavailableFrom'], e['DateOfTheNotification'], e['Company']])
    return f"{TAG_BASE}{e['NordicArticleNumber']}/{hashlib.sha1(key.encode('utf-8')).hexdigest()[:10]}/{kind}"


def _critical_text(c, lang):
    t = TEXT[lang]
    d = lambda value: date_text(value, lang)
    name = ' '.join(x for x in (c.get('medicine'), strength_label(c.get('strength'), lang)) if x) or f"VNR {c['vnrs'][0]}"
    def package(p):
        pack = (p.get('pack_label') or {}).get(lang, '')
        return ', '.join(x for x in (name_with_strength(p['name'], p['strength'], lang, pack), pack, f"VNR {p['vnr']}") if x)
    return f"{t['critical']}: {name}", '\n'.join([t['critical_when'](d(c['date']), d(c['after'])), t['critical_advice'], f"{t['listed']}: {'; '.join(map(package, c['packages']))}"])


def feeds(es, snapshots, history, critical=()):
    """Return {'feed.xml': ..., 'feed-fi.xml': ...} with one entry per new and per removed event in the last 14 days, and one per
    substitution group that newly has no interchangeable product on the market (`critical`); newest 200 at most."""
    latest = history[-1]['date']
    cutoff = _shift(latest, FEED_DAYS)
    new, left = _arrivals_and_exits(es, snapshots, cutoff)
    entries = [(e['first_seen'], 'new', e) for e in new] + [(e['removed_on'], 'left', e) for e in left]
    entries += [(c['date'], 'critical', c) for c in critical if c['date'] > cutoff]
    entries.sort(key=lambda x: (x[0], x[1], x[2].get('NordicArticleNumber') or x[2].get('group')), reverse=True)
    entries = entries[:FEED_MAX_ENTRIES]
    out = {}
    for lang, t in TEXT.items():
        parts = ['<?xml version="1.0" encoding="utf-8"?>', f'<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="{lang}">',
                 f'<id>{SITE_URL}{t["file"]}</id>', f'<title>{escape(t["title"])}</title>', f'<subtitle>{escape(t["subtitle"])}</subtitle>',
                 f'<updated>{latest}T00:00:00Z</updated>', f'<link rel="self" type="application/atom+xml" href="{SITE_URL}{t["file"]}"/>', f'<link rel="alternate" type="text/html" href="{SITE_URL}"/>',
                 '<author><name>Shortage Radar</name>' + f'<uri>{SITE_URL}</uri></author>', '<rights>Data: Finnish Medicines Agency Fimea, CC BY 4.0. Selected, joined and transformed.</rights>']
        for day, kind, e in entries:
            if kind == 'critical':
                title, body = _critical_text(e, lang)
                parts.append(f'<entry><id>{TAG_BASE}group/{e["group"]}/{e["date"]}/critical</id><title>{escape(title)}</title><updated>{day}T00:00:00Z</updated><link rel="alternate" type="text/html" href="{SITE_URL}medicine.html?vnr={e["vnrs"][0]}"/><summary type="text">{escape(body)}</summary></entry>')
                continue
            title, body = _entry_text(e, lang, kind)
            parts.append(f'<entry><id>{_entry_id(e, kind)}</id><title>{escape(title)}</title><updated>{day}T00:00:00Z</updated><link rel="alternate" type="text/html" href="{SITE_URL}medicine.html?vnr={e['NordicArticleNumber']}"/><summary type="text">{escape(body)}</summary></entry>')
        parts.append('</feed>')
        out[t['file']] = '\n'.join(parts) + '\n'
    return out
