"""Text of the EU critical medicines pages, in English and Finnish.

Every text block is written into the page twice, `<span class="l-en" lang="en">` and `<span class="l-fi" lang="fi">`, and the style sheet shows the one that
matches `<html lang>` (site/language.js sets it, the language buttons change it), so a language change needs no reload and no script for the text.
Option labels, placeholders and aria-labels cannot hold spans: they carry `data-en` / `data-fi` and site/critical.js swaps them.

COPY maps a key to (English, Finnish). The English text is what the pages said before. The Finnish text is a DRAFT (not checked by a native reviewer);
it uses the terms of site/i18n.js (saatavuushäiriö, vaihtokelpoinen pakkaus, tilannekuva, Antoreitti) and keeps EU-source names (EMA, ATC, VNR) as they are.
A template may hold markup; its fields are escaped unless they are `Raw`. A field is one value, or a pair (English, Finnish).
"""
from html import escape

from changes import date_text
from critical_copy_methods import METHODS


class Raw(str):
    """HTML that is already safe."""


def esc(value):
    return value if isinstance(value, Raw) else escape(str(value if value is not None else ''), quote=True)


def both(en, fi):
    """Two language versions of data text (escaped here); one plain text when the two are the same."""
    return esc(en) if en == fi else bi(esc(en), esc(fi))


def bi(en, fi):
    """Two language versions of one piece of text (both already safe HTML)."""
    return f'<span class="l-en" lang="en">{en}</span><span class="l-fi" lang="fi">{fi}</span>'


def num(n):
    """A number in each language: 1,234 in English, 1 234 (no-break space) in Finnish."""
    return (f'{n:,}', f'{n:,}'.replace(',', ' '))


def day(value):
    """A date in each language: 21 Nov 2026, 21.11.2026; a missing date reads "not given"."""
    return (date_text(value, 'en') or COPY['row.not_given'][0], date_text(value, 'fi') or COPY['row.not_given'][1])


def days(n):
    return (f'{n} {"day" if n == 1 else "days"}', f'{n} {"päivä" if n == 1 else "päivää"}')


def fmt(key, index, fields):
    return COPY[key][index].format(**{k: esc(v[index] if isinstance(v, tuple) else v) for k, v in fields.items()})


def t(key, **fields):
    """The text for `key` in both languages."""
    return bi(fmt(key, 0, fields), fmt(key, 1, fields))


def plain(key, index, **fields):
    """The text for `key` in one language (0 English, 1 Finnish), for places that take no markup; it is not escaped again."""
    return COPY[key][index].format(**{k: (v[index] if isinstance(v, tuple) else v) for k, v in fields.items()})


def swap(key, **fields):
    """Attributes that make site/critical.js show the text of `key` in the current language (for option, SVG title)."""
    return f' data-en="{esc(plain(key, 0, **fields))}" data-fi="{esc(plain(key, 1, **fields))}"'


def swap_attr(name, key, **fields):
    """The same for an attribute (placeholder, aria-label): the value is the English text, `data-<lang>-<name>` hold both."""
    en, fi = esc(plain(key, 0, **fields)), esc(plain(key, 1, **fields))
    return f' {name}="{en}" data-eu-attr="{name}" data-en-{name}="{en}" data-fi-{name}="{fi}"'


# ATC level 1 groups, named as the WHO names them (English) and as the Finnish ATC classification names them (draft).
ATC_GROUPS_FI = {
    'A': 'Ruoansulatuskanava ja aineenvaihdunta', 'B': 'Veri ja verta muodostavat elimet', 'C': 'Sydän ja verenkiertoelimistö', 'D': 'Ihotaudit',
    'G': 'Virtsa- ja sukupuolielimet sekä sukupuolihormonit', 'H': 'Systeemiset hormonivalmisteet', 'J': 'Infektiolääkkeet systeemiseen käyttöön',
    'L': 'Syöpälääkkeet ja immuunivasteen muuntajat', 'M': 'Tuki- ja liikuntaelimistö', 'N': 'Hermosto', 'P': 'Loislääkkeet',
    'R': 'Hengityselimet', 'S': 'Aistielimet', 'V': 'Muut',
}
ROUTE_NAMES_FI = {'injection': 'Injektio tai infuusio', 'oral': 'Suun kautta tai kielen alle', 'eye': 'Silmään', 'other': 'Muu tai sekalainen antoreitti'}
TYPE_NAMES_FI = {'exact': 'Täsmällinen osuma', 'route-mismatch': 'Antoreitti ei sovi', 'unmatched': 'Ei rekisterissä', 'ingredient-mismatch': 'Vaikuttavaa ainetta ei vahvistettu',
                 'flag-only': 'Vain Fimean merkitsemä'}
STATUS_NAMES_FI = {'ongoing': 'Käynnissä', 'upcoming': 'Alkaa myöhemmin'}

COPY = {
    # --- page titles and descriptions (document title and meta description; critical.js swaps them)
    'title': ('EU critical medicines list: shortages in Finland', 'EU:n kriittisten lääkkeiden luettelo: saatavuushäiriöt Suomessa'),
    'site': ('Shortage Radar', 'Saatavuustutka'),
    'meta.list': ('Medicines on the EU Union list of critical medicines that Fimea lists as short in Finland, matched by ATC code and route.',
                  'EU:n kriittisten lääkkeiden unionin luettelon lääkkeet, joilla Fimean listalla on saatavuushäiriö Suomessa, yhdistettynä ATC-koodin ja antoreitin mukaan.'),
    'meta.code': ('Fimea shortage notices, the EU list row and the archive history for ATC code {code}.',
                  'Fimean saatavuushäiriöilmoitukset, EU:n luettelon rivi ja arkistohistoria ATC-koodille {code}.'),
    'code.titlesuffix': ('Critical medicines', 'Kriittiset lääkkeet'),
    'methods.title': ('How the critical medicines match works', 'Miten kriittisten lääkkeiden täsmäys toimii'),
    'meta.methods': ('Sources, licences, the match rule and the limits of the critical medicines page.',
                     'Kriittisten lääkkeiden sivun lähteet, lisenssit, täsmäyssääntö ja rajoitukset.'),

    # --- the short line under every title (no advice, not a stock check) and the explanation of "critical" (moved into Details)
    'lead.list': ('Medicines on the EU critical list that Fimea lists as short in Finland.',
                  'EU:n kriittisten lääkkeiden luettelon lääkkeet, joilla Fimean listalla on saatavuushäiriö Suomessa.'),
    'lead.code': ('ATC code {code} is on the EU critical list, version {version}.', 'ATC-koodi {code} on EU:n kriittisten lääkkeiden luettelossa, versio {version}.'),
    'lead.methods': ('Which sources we use, how a shortage is matched to the EU list, and what the match cannot tell you.',
                     'Mitä lähteitä käytämme, miten saatavuushäiriö yhdistetään EU:n luetteloon ja mitä täsmäys ei kerro.'),
    'advice.short': ('Not medical advice. A listing does not show pharmacy stock.', 'Ei lääketieteellinen neuvo. Listalla oleminen ei kerro apteekin varastosta.'),
    'explained': ('The EU list names medicines whose continuous supply the EU treats as a priority. It does not rate how serious a shortage is for you. '
                  'It is not the same as this site’s label ‘{substitute}’ / ‘{no_alternative}’.',
                  'EU:n luettelossa ovat lääkkeet, joiden jatkuvaa saatavuutta EU pitää ensisijaisen tärkeänä. Luettelo ei kerro, kuinka vakava häiriö on sinulle, '
                  'eikä se ole sama asia kuin tämän sivuston merkintä ”{substitute}” / ”{no_alternative}”.'),
    'impact.substitute': ('Interchangeable package found in the data', 'Vaihtokelpoinen pakkaus löytyy aineistosta'),
    'impact.no_alternative': ('No interchangeable package found in the data', 'Aineistosta ei löydy vaihtokelpoista pakkausta'),
    'back': ('EU critical medicines list: shortages in Finland', 'EU:n kriittisten lääkkeiden luettelo: saatavuushäiriöt Suomessa'),

    # --- match types
    'type.exact': ('The ATC code is on the EU list, the active ingredient is the list substance and a route of the product fits a route of the list row.',
                   'ATC-koodi on EU:n luettelossa, vaikuttava aine on luettelon aine ja valmisteen antoreitti sopii luettelon rivin antoreittiin.'),
    'type.route-mismatch': ('The ATC code and ingredient are on the EU list, but no route of the product fits the list row, or Fimea gives no usable route.',
                            'ATC-koodi ja vaikuttava aine ovat EU:n luettelossa, mutta mikään valmisteen antoreitti ei sovi luettelon riviin tai Fimea ei anna käyttökelpoista antoreittiä.'),
    'type.ingredient-mismatch': ('The ATC code is on the EU list, but the list substance is not among the active ingredients of the product, or no ingredients are given.',
                                 'ATC-koodi on EU:n luettelossa, mutta luettelon aine ei ole valmisteen vaikuttavien aineiden joukossa tai vaikuttavia aineita ei ole annettu.'),
    'type.unmatched': ('The VNR is not in the Fimea register, so the code is not known.', 'VNR ei ole Fimean rekisterissä, joten koodi ei ole tiedossa.'),
    'tile.exact': (' Of {checked} checked against the EU list, {exact} are exact.', ' Tarkistetuista käynnissä olevista pakkauksista ({n}) täsmällisiä on {exact}.'),
    'tile.later': (' {n} more start later.', ' Lisäksi {n} alkaa myöhemmin.'),
    'tile.info': ('About: {label}', 'Lisätietoa: {label}'),
    'n.ongoing': ('{n} ongoing package', '{n} käynnissä oleva pakkaus'),
    'n.ongoing.many': ('{n} ongoing packages', '{n} käynnissä olevaa pakkausta'),
    'n.ongoing.gen': ('{n} ongoing package', '{n} käynnissä olevan pakkauksen'),
    'n.ongoing.gen.many': ('{n} ongoing packages', '{n} käynnissä olevan pakkauksen'),
    'n.checked': ('{n} checked package', '{n} tarkistetulla pakkauksella'),
    'n.checked.many': ('{n} checked packages', '{n} tarkistetulla pakkauksella'),

    # --- the list page
    'counts.title': ('Ongoing packages by match', 'Käynnissä olevat pakkaukset täsmäyksen mukaan'),
    'details.list': ('Details: what “critical” means, notes, sources', 'Lisätiedot: mitä ”kriittinen” tarkoittaa, huomautukset, lähteet'),
    'details.code': ('Details: what “critical” means, notes, sources', 'Lisätiedot: mitä ”kriittinen” tarkoittaa, huomautukset, lähteet'),
    'list.version': ('EU list version {version}.', 'EU:n luettelon versio {version}.'),
    'notes.advice': ('<strong>This is not medical advice.</strong> A listing does not tell you whether a medicine is available at your pharmacy. Ask a pharmacist or doctor.',
                     '<strong>Tämä ei ole lääketieteellinen neuvo.</strong> Listalla oleminen ei kerro, onko lääkettä apteekissasi. Kysy apteekista tai lääkäriltä.'),
    'notes.advice.code': ('<strong>This is not medical advice.</strong> A listing does not tell you whether a medicine is available at your pharmacy. Ask a pharmacist or doctor. '
                          '<a href="{methods}">How the match works</a>',
                          '<strong>Tämä ei ole lääketieteellinen neuvo.</strong> Listalla oleminen ei kerro, onko lääkettä apteekissasi. Kysy apteekista tai lääkäriltä. '
                          '<a href="{methods}">Miten täsmäys toimii</a>'),
    'later.some': ('<strong>Starts later.</strong> {pkg} {has} a notice that has not started yet ({split}). They are in the list, marked “Starts later”, and are not in the numbers above.',
                   '<strong>Alkaa myöhemmin.</strong> {pkg} on ilmoitus, joka ei ole vielä alkanut ({split}). Ne ovat listassa merkittyinä ”Alkaa myöhemmin”, eivätkä ne ole yllä olevissa luvuissa.'),
    'later.none': ('<strong>Starts later.</strong> No notice that starts later is listed. Such a notice would be marked “Starts later” and kept out of the numbers above.',
                   '<strong>Alkaa myöhemmin.</strong> Listalla ei ole ilmoitusta, joka alkaa myöhemmin. Sellainen ilmoitus merkittäisiin ”Alkaa myöhemmin” eikä se olisi yllä olevissa luvuissa.'),
    'flag': ('<strong>Fimea’s flag differs.</strong> Fimea’s own EU-critical flag differs from this match (exact match, route does not fit or ingredient not confirmed) for {pkg}{more}. The row note says so.',
             '<strong>Fimean merkintä poikkeaa.</strong> Fimean oma EU-kriittisyysmerkintä poikkeaa tästä täsmäyksestä (täsmällinen osuma, antoreitti ei sovi tai vaikuttavaa ainetta ei vahvistettu) {pkg} kohdalla{more}. Rivin huomautus kertoo tämän.'),
    'flag.more': (', and Fimea flags {n} more whose ATC code is not on the list', ', ja Fimea merkitsee lisäksi {n} pakkausta, joiden ATC-koodi ei ole luettelossa'),
    'notes.end': ('<strong>Estimated end.</strong> End dates are the company’s estimates. Fimea’s file keeps no history and its dates can change.',
                  '<strong>Arvioitu päättyminen.</strong> Päättymispäivät ovat yrityksen arvioita. Fimean tiedosto ei säilytä historiaa, ja sen päivämäärät voivat muuttua.'),
    'notes.data': ('<strong>Data.</strong> Fimea file saved <time datetime="{iso}">{date}</time>.', '<strong>Aineisto.</strong> Fimean tiedosto tallennettu <time datetime="{iso}">{date}</time>.'),
    'source.short': ('Sources: European Medicines Agency (EU list) and Fimea (shortages, <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>). We selected, joined and changed the data.',
                     'Lähteet: Euroopan lääkevirasto EMA (EU:n luettelo) ja Fimea (saatavuushäiriöt, <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>). Valitsimme, yhdistimme ja muokkasimme aineistoa.'),
    'source.full': ('Full source credit', 'Täydet lähdetiedot'),
    'source.snapshot': ('Archive snapshot of {date}. Times are file modification times (HTTP Last-Modified); Fimea gives no release times.',
                        'Arkiston tilannekuva {date}. Ajat ovat tiedostojen muokkausaikoja (HTTP Last-Modified); Fimea ei ilmoita julkaisuaikoja.'),
    'source.english': ('', 'Lähdetiedot ovat englanniksi, koska ne seuraavat mukana ladattavissa tiedostoissa.'),
    'notes.links': ('<a href="{methods}">How the match works</a> · <a href="{methods}#types">What the match types mean</a>',
                    '<a href="{methods}">Miten täsmäys toimii</a> · <a href="{methods}#types">Mitä täsmäystyypit tarkoittavat</a>'),
    'empty.list': ('No shortage packages match the EU list today.', 'Yksikään saatavuushäiriöpakkaus ei täsmää EU:n luetteloon tänään.'),
    'charts.fold': ('Exact matches by ATC group and route', 'Täsmälliset osumat ATC-ryhmän ja antoreitin mukaan'),
    'table.title': ('Shortage packages', 'Saatavuushäiriöpakkaukset'),
    'filter.search': ('Search', 'Haku'),
    'filter.placeholder': ('Name, substance, ATC code, company or VNR', 'Nimi, vaikuttava aine, ATC-koodi, yritys tai VNR'),
    'filter.match': ('Match', 'Täsmäys'),
    'filter.all': ('All matches', 'Kaikki täsmäykset'),
    'filter.status': ('Status', 'Tila'),
    'filter.status.all': ('Ongoing and starts later', 'Käynnissä ja alkaa myöhemmin'),
    'status.ongoing': ('Ongoing', 'Käynnissä'),
    'status.upcoming': ('Starts later', 'Alkaa myöhemmin'),
    'pager.label': ('Pages of shortage packages', 'Saatavuushäiriöpakkausten sivut'),
    'th.medicine': ('Medicine', 'Lääke'),
    'th.atc': ('ATC code', 'ATC-koodi'),
    'th.match': ('Match', 'Täsmäys'),
    'th.status': ('Status', 'Tila'),
    'th.end': ('Estimated end', 'Arvioitu päättyminen'),
    'row.ongoing': ('Ongoing <span class="note">reported start {date}</span>', 'Käynnissä <span class="note">ilmoitettu alkamispäivä {date}</span>'),
    'row.later': ('Starts later <span class="note">on {date}</span>', 'Alkaa myöhemmin <span class="note">{date}</span>'),
    'row.details': ('Details', 'Lisätiedot'),
    'row.company': ('Company', 'Yritys'),
    'row.start': ('Reported start', 'Ilmoitettu alkamispäivä'),
    'row.route': ('Route', 'Antoreitti'),
    'row.product_route': ('Product route', 'Valmisteen antoreitti'),
    'row.list_route': ('List route', 'Luettelon antoreitti'),
    'row.not_known': ('not known', 'ei tiedossa'),
    'row.not_given': ('not given', 'ei ilmoitettu'),
    'row.vnr': ('VNR', 'VNR'),
    'dl.notified': ('Notification date', 'Ilmoituspäivä'),
    'dl.end': ('Estimated end', 'Arvioitu päättyminen'),
    'dl.package': ('Package', 'Pakkaus'),
    'dl.between': ('Days between captures', 'Päiviä tilannekuvien välillä'),
    'unknown': ('unknown', 'ei tiedossa'),
    'download.title': ('Download', 'Lataa'),
    'download.csv': ('All matches (CSV)', 'Kaikki täsmäykset (CSV, englanniksi)'),
    'download.json': ('All matches (JSON)', 'Kaikki täsmäykset (JSON, englanniksi)'),
    'download.rss': ('Alerts: new shortages (RSS)', 'Hälytykset: uudet saatavuushäiriöt (RSS, englanniksi)'),
    'download.feed': ('Alerts: new shortages (JSON feed)', 'Hälytykset: uudet saatavuushäiriöt (JSON-syöte, englanniksi)'),
    'codes.fold': ('All {n} codes on the EU list', 'Kaikki {n} EU:n luettelon koodia'),
    'codes.archive': ('{n} in archive', '{n} arkistossa'),

    # --- notes of a row (the English text is the note that critical.py writes; a test keeps the two in step)
    'note.unmatched': ('This VNR is not in the Fimea register, so its ATC code and route are not known.', 'Tämä VNR ei ole Fimean rekisterissä, joten sen ATC-koodi ja antoreitti eivät ole tiedossa.'),
    'note.flag-only': ('Fimea flags this product as EU-critical, but its ATC code is not on the EU list.', 'Fimea merkitsee tämän valmisteen EU-kriittiseksi, mutta sen ATC-koodi ei ole EU:n luettelossa.'),
    'note.ingredient-mismatch': ('The ATC code is on the list, but the active ingredient is not confirmed. List substance: {list}. Product ingredients: {have}.',
                                 'ATC-koodi on luettelossa, mutta vaikuttavaa ainetta ei ole vahvistettu. Luettelon aine: {list}. Valmisteen vaikuttavat aineet: {have}.'),
    'note.none_given': ('none given', 'ei annettu'),
    'note.exact': ('The ATC code and the active ingredient are on the list and the route fits.', 'ATC-koodi ja vaikuttava aine ovat luettelossa ja antoreitti sopii.'),
    'note.unclear': ('The ATC code is on the list. Route unclear: Fimea gives no usable route for this product, so no route match is made.',
                     'ATC-koodi on luettelossa. Antoreitti epäselvä: Fimea ei anna tälle valmisteelle käyttökelpoista antoreittiä, joten antoreittiä ei täsmätä.'),
    'note.route-mismatch': ('The ATC code is on the list, but the route does not fit. Product route: {product}. List route: {list}.',
                            'ATC-koodi on luettelossa, mutta antoreitti ei sovi. Valmisteen antoreitti: {product}. Luettelon antoreitti: {list}.'),
    'note.flag0.exact': ('Fimea does not flag this product as EU-critical; the ATC code, ingredient and route match the list.',
                         'Fimea ei merkitse tätä valmistetta EU-kriittiseksi; ATC-koodi, vaikuttava aine ja antoreitti täsmäävät luetteloon.'),
    'note.flag0': ('Fimea does not flag this product as EU-critical.', 'Fimea ei merkitse tätä valmistetta EU-kriittiseksi.'),
    'note.flag1': ('Fimea flags this product as EU-critical.', 'Fimea merkitsee tämän valmisteen EU-kriittiseksi.'),

    # --- charts
    'chart.routes.label': ('Ongoing exact matches by route of the product', 'Käynnissä olevat täsmälliset osumat valmisteen antoreitin mukaan'),
    'chart.groups.caption': ('Exact matches by ATC group (first letter of the code)', 'Täsmälliset osumat ATC-ryhmän mukaan (koodin ensimmäinen kirjain)'),
    'chart.groups.table': ('Exact matches by ATC group', 'Täsmälliset osumat ATC-ryhmän mukaan'),
    'chart.group': ('ATC group', 'ATC-ryhmä'),
    'chart.ongoing': ('Ongoing', 'Käynnissä'),
    'chart.later': ('Starts later', 'Alkaa myöhemmin'),
    'chart.strip.caption': ('Timeline of shortages, newest first', 'Saatavuushäiriöiden aikajana, uusin ensin'),
    'chart.strip.listed': ('Listed', 'Listalla'),
    'chart.strip.unknown': ('Start unknown', 'Alkamisajankohta ei tiedossa'),
    'chart.strip.nocapture': ('No capture (unknown)', 'Ei tilannekuvaa (ei tiedossa)'),
    'chart.strip.aria': ('Timeline strip: one bar for each of {n} shortages. The list below has the same facts.', 'Aikajanakaavio: yksi palkki kutakin {n} saatavuushäiriötä kohti. Alla oleva luettelo sisältää samat tiedot.'),
    'chart.strip.label': ('{name}: first seen {first}, {state}{unknown}{gaps}', '{name}: ensimmäisen kerran nähty {first}, {state}{unknown}{gaps}'),
    'chart.strip.still': ('still listed', 'edelleen listalla'),
    'chart.strip.last': ('last seen {date}', 'viimeksi nähty {date}'),
    'chart.strip.unknownstart': (', start unknown', ', alkamisajankohta ei tiedossa'),
    'chart.strip.gap': (', not observed between {a} and {b}', ', ei havaittu välillä {a}–{b}'),
    'chart.strip.gaptitle': ('Not observed between {a} and {b}', 'Ei havaittu välillä {a}–{b}'),
    'chart.strip.unseentitle': ('Not listed in the captures {a} to {b}: unknown', 'Ei listalla tilannekuvissa {a}–{b}: ei tiedossa'),

    # --- the code page
    'tile.substance': ('Substance', 'Vaikuttava aine'),
    'tile.atcsub': ('ATC code {code}', 'ATC-koodi {code}'),
    'tile.status': ('Status in the latest capture', 'Tila viimeisimmässä tilannekuvassa'),
    'tile.ongoing': ('{n} ongoing', '{n} käynnissä'),
    'tile.noneongoing': ('None ongoing', 'Ei käynnissä olevia'),
    'tile.startlater': ('{n} start later', '{n} alkaa myöhemmin'),
    'tile.nomatch': ('No notice matched in the latest capture', 'Ei yhdistettyä ilmoitusta viimeisimmässä tilannekuvassa'),
    'tile.nomatch.sub': ('Capture of {date}. This does not show stock.', 'Tilannekuva {date}. Tämä ei kerro varastosta.'),
    'tile.last': ('Last notice', 'Viimeisin ilmoitus'),
    'tile.last.sub': ('Notification date', 'Ilmoituspäivä'),
    'tile.last.seen': ('Last seen in our archive', 'Viimeksi nähty arkistossamme'),
    'tile.none': ('None', 'Ei yhtään'),
    'tile.none.sub': ('None in our archive', 'Ei arkistossamme'),
    'h.now': ('Fimea notices in the latest capture', 'Fimean ilmoitukset viimeisimmässä tilannekuvassa'),
    'h.history': ('History', 'Historia'),
    'h.list': ('EU list row', 'EU:n luettelon rivi'),
    'nonotice': ('No notice was matched to this code in the latest capture ({date}). This does not show stock.',
                 'Tähän koodiin ei yhdistetty Fimean ilmoitusta viimeisimmässä tilannekuvassa ({date}). Tämä ei kerro varastosta.'),
    'list.atc': ('ATC code', 'ATC-koodi'),
    'list.substance': ('Substance on the list', 'Luettelon aine'),
    'list.routes': ('Routes on the list', 'Luettelon antoreitit'),
    'list.included': ('Date of inclusion', 'Lisäyspäivä luetteloon'),
    'list.version.label': ('List version', 'Luettelon versio'),
    'list.row': ('Row in the EMA file', 'Rivi EMAn tiedostossa'),

    # --- history
    'hist.none': ('No shortage for this code is in our archive.', 'Tämän koodin saatavuushäiriöitä ei ole arkistossamme.'),
    'hist.count': ('Our archive holds {n} {word} for packages with this code since {since}: {now} listed now, {gone} no longer listed.',
                   'Arkistossamme on {n} {word} tämän koodin pakkauksista {since} alkaen: {now} on nyt listalla, {gone} ei enää listalla.'),
    'hist.shortage': ('shortage', 'saatavuushäiriö'),
    'hist.shortages': ('shortages', 'saatavuushäiriötä'),
    'hist.measured': ('For {m} no longer listed shortages whose start we know and with no gap in the captures, the days between the first and the last capture that listed them were '
                      '{min} at least, {med} in the middle and {max} at most. '
                      'These are days between captures, not exact lengths: a shortage may have started before the first capture and lasted after the last.',
                      'Niistä {m} listalta poistuneesta saatavuushäiriöstä, joiden alkamisajankohta tunnetaan ja joiden tilannekuvissa ei ole aukkoa, ensimmäisen ja viimeisen niitä listanneen tilannekuvan välillä oli päiviä '
                      'vähintään {min}, mediaanina {med} ja enintään {max}. '
                      'Nämä ovat päiviä tilannekuvien välillä, eivät tarkkoja kestoja: häiriö on voinut alkaa ennen ensimmäistä tilannekuvaa ja jatkua viimeisen jälkeen.'),
    'hist.nomeasure': ('No shortage that left the list has a known start and a gap-free record, so no days between captures can be given.',
                       'Millään listalta poistuneella saatavuushäiriöllä ei ole tunnettua alkamisajankohtaa ja aukotonta tilannekuvajaksoa, joten päiviä tilannekuvien välillä ei voi antaa.'),
    'hist.earlier': ('Show {n} earlier {word}', 'Näytä {n} {word}'),
    'hist.earlier.one': ('shortage', 'aiempi saatavuushäiriö'),
    'hist.earlier.many': ('shortages', 'aiempaa saatavuushäiriötä'),
    'hist.newest': ('Newest first. “Start unknown”: see “How to read this history” below.', 'Uusin ensin. ”Alkamisajankohta ei tiedossa”: katso alla ”Miten tämä historia luetaan”.'),
    'hist.how': ('How to read this history', 'Miten tämä historia luetaan'),
    'hist.how1': ('“Start unknown” means the notice was already listed in the first capture, or the capture before its first sighting is more than {max} days earlier.',
                  '”Alkamisajankohta ei tiedossa” tarkoittaa, että ilmoitus oli jo listalla ensimmäisessä tilannekuvassa tai sen ensimmäistä havaintoa edeltävä tilannekuva on yli {max} päivää aiemmin.'),
    'hist.how2': ('A notice that Fimea edited, or that was missing from some captures and came back, is counted as one shortage. '
                  'The archive is made of captures of Fimea’s file, not daily readings; before 21 Nov 2026 the captures come from the Internet Archive and have gaps. '
                  'A gap in the captures is unknown time: it is not a new start and not an end. The start of a shortage is unknown when it was already listed in the first capture, or when the capture before its first sighting is more than 14 days earlier. '
                  '“Last seen” is the last capture that listed the shortage. A shortage that is not listed any more is not proof that supply returned.',
                  'Ilmoitus, jota Fimea on muokannut tai joka puuttui joistakin tilannekuvista ja palasi, lasketaan yhdeksi saatavuushäiriöksi. '
                  'Arkisto koostuu Fimean tiedoston tilannekuvista, ei päivittäisistä lukemista; ennen 21.11.2026 tilannekuvat ovat peräisin Internet Archivesta ja niissä on aukkoja. '
                  'Aukko tilannekuvissa on tuntematonta aikaa: se ei ole uusi alku eikä loppu. Saatavuushäiriön alkamisajankohta ei ole tiedossa, kun se oli jo listalla ensimmäisessä tilannekuvassa tai kun sen ensimmäistä havaintoa edeltävä tilannekuva on yli 14 päivää aiemmin. '
                  '”Viimeksi nähty” on viimeinen tilannekuva, jossa saatavuushäiriö oli listalla. Se, ettei saatavuushäiriö ole enää listalla, ei todista, että saatavuus on palautunut.'),
    'step.still': ('Still listed', 'Edelleen listalla'),
    'step.last': ('Last seen {date}', 'Viimeksi nähty {date}'),
    'step.first.capture': ('Listed in the first capture ({date}). Start unknown.', 'Listalla ensimmäisessä tilannekuvassa ({date}). Alkamisajankohta ei tiedossa.'),
    'step.first.gap': ('First seen {date}. Start unknown: no capture for {n} days before it.', 'Ensimmäisen kerran nähty {date}. Alkamisajankohta ei tiedossa: tilannekuvaa ei ole {n} päivältä ennen sitä.'),
    'step.first': ('First seen {date}', 'Ensimmäisen kerran nähty {date}'),
    'step.package': ('VNR {vnr}, {company}', 'VNR {vnr}, {company}'),
    'step.edited': ('Notice edited {n} {word}; counted as one shortage.', 'Ilmoitusta muokattu {n} {word}; lasketaan yhdeksi saatavuushäiriöksi.'),
    'step.time': ('time', 'kerran'),
    'step.times': ('times', 'kertaa'),
    'step.unseen': ('Not listed in the captures between {a} and {b}: unknown.', 'Ei listalla tilannekuvissa {a}–{b}: ei tiedossa.'),
    'step.unobserved': ('Not observed between {a} and {b}.', 'Ei havaittu välillä {a}–{b}.'),
}

COPY.update(METHODS)
