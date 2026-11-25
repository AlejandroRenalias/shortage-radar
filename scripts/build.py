"""Build a static dataset from Fimea snapshots and its basic register."""
import csv
from collections import Counter
import json
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
import os
import re
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo

import critical as eu_list
from changes import _shift, feeds, week_summary
from gaps import MAX_GAP_DAYS, add_capture, days_between, gaps_of, is_gap
from medicine_pages import build_pages
from packs import pack_label
from pages import render_pages
from removed import removed_index
from slices import package_shards, summary
from source_age import register_date
from triage import is_available_alternative, level, medicine_name, newly_critical

ROOT = Path(__file__).resolve().parents[1]
# MAX_GAP_DAYS (scripts/gaps.py): captures further apart than this are not joined into one continuous series,
# and a change of an end date across a wider gap is not counted (end_date_changes).
# Product fields kept out of the shortage events: the holder, and the route and flag details the critical medicines join reads.
PRIVATE = {'holder', 'routes', 'eu_flag', 'form_id', 'atc_name'}
CC_BY = 'https://creativecommons.org/licenses/by/4.0/'


def fimea_credit(sources):
    """The credit that goes with every copy of the shortage data (CSV, JSON): Fimea, the file times, the licence and the note that the data was changed.
    The EU list files carry their own credit (critical.credit), which names EMA as well."""
    modified = lambda key: f"file modification time {sources[key]} (HTTP Last-Modified)" if sources.get(key) else 'file modification time not recorded'
    return (f"Shortages: Finnish Medicines Agency Fimea, file Shortages.txt (also published as Saatavuushairiot.txt), {modified('shortages_last_modified')}. "
            f"Register: Fimea, file {sources.get('register_file') or 'Perusrekisteri (year not recorded)'}, {modified('register_last_modified')}. "
            f"Fimea data is licensed under CC BY 4.0 ({CC_BY}). Shortage Radar selected, joined and changed the data; Fimea does not endorse the result. "
            "The impact column or field is Shortage Radar's own reading of Fimea's files, not a Fimea field.")


def week_file(week, metadata):
    """week.json carries the source credit too. The summary is null when there are too few captures, and stays null."""
    return None if week is None else dict(week, source_metadata=metadata)


HEADER = ['NordicArticleNumber', 'Valid', 'UnavailableFrom', 'EndingDate', 'DateOfTheNotification', 'Updated', 'Company']


def helsinki_today():
    return datetime.now(ZoneInfo('Europe/Helsinki')).date().isoformat()


def read_snapshot(path):
    if not path.read_bytes().endswith(b'\n'):
        raise ValueError(f'{path}: missing final newline')
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, delimiter=';', strict=True)
        if reader.fieldnames != HEADER:
            raise ValueError(f'{path}: unexpected header')
        rows = list(reader)
    if not rows:
        raise ValueError(f'{path}: no rows')
    seen = set()
    for row in rows:
        if None in row or any(row[k] is None for k in HEADER) or not row['NordicArticleNumber'].isdigit() or len(row['NordicArticleNumber']) != 6:
            raise ValueError(f'{path}: malformed row {row}')
        if any(not row[k].strip() for k in HEADER):
            raise ValueError(f'{path}: empty required field')
        key = tuple(row[k] for k in ('NordicArticleNumber', 'UnavailableFrom', 'DateOfTheNotification', 'Company'))
        if key in seen:
            raise ValueError(f'{path}: duplicate event identity {key}')
        seen.add(key)
        for k in ('UnavailableFrom', 'EndingDate', 'DateOfTheNotification', 'Updated'):
            if row[k]:
                date.fromisoformat(row[k])
    return rows


def group_key(product):
    """Fimea's substitution group code decides interchangeability; strength and form text are not compared because the
    register writes them differently inside one group ("20 mg/ml" and "20 mg/g", film-coated tablets and capsules)."""
    return ' '.join(unicodedata.normalize('NFKC', product.get('substitution_group', '')).split()) or None


def one_word_substance_name(atc, name):
    """The Finnish ATC name of a full ATC code when it is one word ("tadalafiili"), else ''.
    The name of a group, a class or a combination ("progesteronia sisältävä muovikierukka") is not a substance name."""
    name = (name or '').strip().lower()
    ok = len(atc or '') == (8 if (atc or '').startswith('Q') else 7) and re.fullmatch(r'[^\W\d_]{5,}', name) and not name.endswith('t') and not any(w in name for w in CLASS_WORDS)
    return name if ok else ''


def _sound(word):
    """A check spelling for one English substance word and its Finnish name: "metyyliprednisoloni" and "methylprednisolone" both give
    "metilprednisolon", "gemsitabiini" and "gemcitabine" both give "gemsitabin". Used only to confirm a pair, never to find one."""
    w = re.sub(r'yyli', 'yl', word.lower())
    w = re.sub(r'ph', 'f', w)
    w = re.sub(r'c(?=[eiy])', 's', w)
    w = re.sub(r'ts', 's', w.replace('h', '').replace('z', 's'))
    w = w.replace('x', 'cs').replace('k', 'c').replace('y', 'i')
    return re.sub(r'(.)\1+', r'\1', w).rstrip('aeiou')


MIN_PRODUCTS = 2
# One-word ATC names that are classes, not substances ("elektrolyytit", "rokotteet", "liuokset"): plural words and generic nouns.
CLASS_WORDS = ('rokote', 'valmiste', 'liuos', 'seos', 'yhdistelm', 'entsyymi')


def finnish_pairs(single):
    """Finnish names for the register's English substance names, from the register itself.

    `single` is an iterable of (substance, atc, atc_name) for products that have exactly one active substance. The whole substance
    name pairs with the one-word ATC name of the product ("Tadalafil" with G04BE08 "tadalafiili"). Nothing is inferred: no shared first
    word, no spelling comparison. A pair is kept only when at least MIN_PRODUCTS products give it and every one agrees; a substance with
    two different Finnish names gets none, and a product whose ATC name is a class ("elektrolyytit") or a label of a code
    ("progesteronia sisältävä muovikierukka") gives nothing. A name that is not kept is left out: no result is better than a wrong one."""
    pairs = {}
    for substance, atc, atc_name in single:
        finnish = one_word_substance_name(atc, atc_name)
        key = ' '.join(re.findall(r'[^\W\d_]+', (substance or '').lower()))
        if finnish and key:
            pairs.setdefault(key, []).append(finnish)
    # A second check on the pair: the Finnish name must spell like one word of the whole English name (so "gemsitabiini" for "Gemcitabine
    # hydrochloride", but not "aprepitantti" for "Fosaprepitant dimeglumine" and not an acid for a salt).
    confirmed = lambda key, finnish: len(_sound(finnish)) >= 5 and _sound(finnish) in {_sound(w) for w in key.split()}
    return {k: v[0] for k, v in pairs.items() if len(set(v)) == 1 and len(v) >= MIN_PRODUCTS and confirmed(k, v[0])}


def search_names(substances, pairs):
    """The Finnish names of a package's active substances, for the search: "levonorgestreeli" for "Levonorgestrel".

    The register writes its active substances (`Aine`) in English only; `finnish_pairs` gives the Finnish names, matched on the whole
    substance name and on nothing else (a salt such as "Meglumine amidotrizoate" is not matched through "Meglumine gadopentate").
    The ATC name of the package itself is not used, because a code can carry a class label. A substance without a name adds nothing.
    The result is a search aid for finding packages. It says nothing about availability."""
    found = [pairs.get(' '.join(re.findall(r'[^\W\d_]+', (substance or '').lower()))) for substance in substances]
    return ' '.join(dict.fromkeys(sorted(x for x in found if x)))


def register(path, wanted, current_shortages=(), members=None, details=None, day=None, names=None, available_out=None):
    """Register details for the wanted VNRs, with the count of other packages in the same substitution group that are
    on the market, not flagged short in the register and not in the current shortage file.

    When `members` is a dict, it is filled with {group: [package]} for every package with a substitution group, for the
    history of the groups and for the list of alternatives on the medicine page.
    When `details` is a dict, it is filled with {vnr: {'routes', 'eu_flag', 'form_id', 'substances'}} for the wanted VNRs:
    what the critical medicines join needs and the other pages do not.
    When `names` is a dict, it is filled with {'trade': Counter of every trade name, 'substances': Counter of every active substance name,
    'strengths': {trade name: set of the strengths the register writes for it}} for the name index (`name_index`).
    When `available_out` is a dict, it is filled with {group: set of the VNRs that are available alternatives} (the sets `other_packages_count` is taken from),
    so a second record of the day's counts (scripts/counts.py) uses the same sets as the ledger and cannot differ.
    `day` (default: today in Helsinki) is the day the register is read for; see triage.is_available_alternative.
    """
    day = day or helsinki_today()
    packages, exact, products, substances = {}, set(), {}, {}
    candidates = []
    pack_refs = set()
    current_shortages = set(current_shortages)
    for _, el in ET.iterparse(path, events=('end',)):
        if el.tag == 'Pakkaus':
            vnr = el.findtext('VNR-numero')
            unit = el.find('Pakkauskokoyksikko')
            package = (el.get('Laakevalmiste-ref'), [x.get('Laakeaine-ref') for x in el.findall('Pakkaus_Laakeaine')], el.findtext('Pakkauskokoteksti', ''), vnr or '', unit.get('value', '') if unit is not None else '')
            old_vnrs = {x.text for x in el.findall('VanhaVNR') if x.text}
            pack_refs.add((el.get('Laakevalmiste-ref'), tuple(package[1])))
            candidates.append((el.get('Laakevalmiste-ref'), vnr, old_vnrs, el.findtext('Kaupanolo/Kaupan'), el.findtext('SaatavuushairioTiedot/Saatavuushairio'),
                               el.findtext('Kaupanolo/Kauppaantulopaiva'), el.findtext('Kaupanolo/Kaupastapoistumispaiva'), package[2], package[4]))
            if vnr in wanted:
                packages[vnr] = package
                exact.add(vnr)
            for old in (x.text for x in el.findall('VanhaVNR')):
                if old in wanted and old not in exact:
                    previous = packages.get(old)
                    if previous is None or (not previous[3] and vnr):
                        packages[old] = package
            el.clear()
        elif el.tag == 'Laakevalmiste':
            atc, form, group = el.find('ATC-koodi'), el.find('Laakemuoto'), el.find('Substituutioryhma')
            routes = [(x.get('id', ''), x.get('value', '')) for x in el.findall('Antoreitti')]
            if names is not None and el.findtext('Kauppanimi', '').strip():
                trade = ' '.join(el.findtext('Kauppanimi', '').split())
                names['trade'][trade] += 1
                # Every strength the register writes for the name, so a label such as "Panadol 500 mg" is found as a label, not only its name.
                names['strengths'].setdefault(trade, set()).add(' '.join(el.findtext('Vahvuus', '').split()))
            products[el.get('id')] = {'routes': routes, 'eu_flag': (el.findtext('EUKriittinenValmiste') or '').strip(), 'form_id': form.get('id', '') if form is not None else '', 'name': el.findtext('Kauppanimi', ''), 'strength': el.findtext('Vahvuus', ''), 'form': form.get('value', '') if form is not None else '', 'atc': atc.get('id', '') if atc is not None else '', 'atc_name': atc.get('value', '') if atc is not None else '', 'substitution_group': group.get('value', '') if group is not None else '', 'holder': el.findtext('Myyntilupa/Haltija', '')}
            el.clear()
        elif el.tag == 'Laakeaine':
            substances[el.get('id')] = [x.get('value', '') for x in el.findall('./VaikuttavaAine/Aine')]
            if names is not None:
                names['substances'].update(' '.join(x.split()) for x in substances[el.get('id')] if x.strip())
            el.clear()
    # Products with one active substance pair that substance with the one-word ATC name of the product (finnish_pairs).
    single = {(ref, names[0]) for ref, refs in pack_refs for names in [list(dict.fromkeys(s for r in refs for s in substances.get(r, []) if s))] if len(names) == 1 and ref in products}
    dictionary = finnish_pairs((substance, products[ref]['atc'], products[ref]['atc_name']) for ref, substance in single)
    if names is not None:
        names['substances'].update(set(dictionary.values()))
    available = {}
    for ref, vnr, old_vnrs, market, shortage, entry, exit_, pack, unit in candidates:
        product = products.get(ref, {})
        key = group_key(product)
        if not (key and vnr):
            continue
        member = {'vnr': vnr, 'old': old_vnrs, 'market': market, 'short': shortage == '1', 'shortage_flag': shortage, 'entry': entry, 'exit': exit_,
                  'name': product['name'], 'strength': product['strength'], 'pack': pack, 'pack_label': pack_label(pack, unit, product['form']), 'company': product['holder']}
        # The same rule as the history of newly critical groups (triage.is_available_alternative); today's register reads the flags.
        if is_available_alternative(member, current_shortages, day, True):
            available.setdefault(key, set()).add(vnr)
        if members is not None:
            members.setdefault(key, []).append(member)
    if available_out is not None:
        available_out.update(available)
    result = {}
    for vnr, (ref, refs, pack, current_vnr, unit) in packages.items():
        if ref in products:
            product = {k: v for k, v in products[ref].items() if k not in PRIVATE}
            key = group_key(product)
            count = len(available.get(key, set()) - {vnr, current_vnr}) if key else 0
            names = list(dict.fromkeys(s for r in refs for s in substances.get(r, []) if s))
            result[vnr] = dict(product, current_vnr=current_vnr, pack=pack, pack_label=pack_label(pack, unit, product['form']), substances=', '.join(names), substance_fi=search_names(names, dictionary), other_packages_count=count)
            if details is not None:
                details[vnr] = dict({k: products[ref][k] for k in ('routes', 'eu_flag', 'form_id')}, substances=names)
    return result


def name_index(names, day=''):
    """The name index for the home page search (site/names.json): every trade name and active substance name of the register, once each.

    A trade name is written "Name|strength|strength": the name, then every strength the register writes for it ("Panadol|125 mg|250 mg|500 mg"),
    so the page can tell a label that is in the register ("Panadol 500 mg") from a strength that is not. A substance is written as its name.
    A name is kept once whatever its case ("PANADOL" and "Panadol"); the spelling used most often wins, then the first in sorted order, and the
    strengths of the spellings are joined. The lists are sorted, so the file is the same for the same register. The index says only that the
    register has the name and strength: it says nothing about shortages or about whether a package is on the market."""
    def unique(counter):
        best = {}
        for name, n in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
            best.setdefault(name.casefold(), name)
        return best
    strengths = names.get('strengths', {})
    trade = unique(names['trade'])
    joined = {}
    for name, strength_set in strengths.items():
        joined.setdefault(name.casefold(), set()).update(x for x in strength_set if x)
    rows = [name + ''.join('|' + x for x in sorted(joined.get(key, ()))) for key, name in trade.items()]
    return {'register_date': day, 'names': sorted(rows, key=lambda x: (x.casefold(), x)),
            'substances': sorted(unique(names['substances']).values(), key=lambda x: (x.casefold(), x))}


def events(snapshots):
    """Track events across captures.

    Captures are days or weeks apart, so every start and end is a window:
    an event began after `first_seen_after` (None for the first capture) and
    no later than `first_seen`; it ended after `last_seen` and no later than
    `removed_on` (None while still listed).

    `first_seen` and `last_seen` are the first and last capture that listed the event. Captures more than MAX_GAP_DAYS
    apart (scripts/gaps.py) are not continuous: `spans` lists the runs of captures ({'first_seen', 'last_seen'}) and
    `gaps` the stretches between them that were not observed ({'from', 'to', 'days'}). `removed_after_gap` is true when the
    capture that no longer lists the event is more than MAX_GAP_DAYS after the last one that did, so the removal date is unknown.
    """
    active, all_events, history = {}, [], []
    previous_day = None
    for day, rows in snapshots:
        # Fimea can publish multiple notifications for a VNR. Notification date
        # and start date distinguish them; exact duplicates are rejected.
        seen = set()
        for row in rows:
            key = (row['NordicArticleNumber'], row['UnavailableFrom'], row['DateOfTheNotification'], row['Company'])
            if key in seen:
                raise ValueError(f'{day}: duplicate event identity {key}')
            seen.add(key)
            if key not in active:
                e = dict(row, first_seen=day, first_seen_after=previous_day, listed_at_first_capture=previous_day is None, last_seen=day, first_estimated_end=row['EndingDate'], end_changes=[{'seen': day, 'date': row['EndingDate']}], removed_on=None, spans=[])
                active[key] = e
                all_events.append(e)
                add_capture(e['spans'], None, day)
            else:
                e = active[key]
                if e['EndingDate'] != row['EndingDate']:
                    e['end_changes'].append({'seen': day, 'date': row['EndingDate']})
                e.update(row, last_seen=day)
                add_capture(e['spans'], previous_day, day)
        listed = {key[0] for key in seen}
        for key in set(active) - seen:
            e = active.pop(key)
            # A changed start date or notification date shows up as a removal plus a new event.
            e.update(removed_on=day, vnr_listed_at_removal=key[0] in listed, removed_after_gap=is_gap(e['last_seen'], day))
        history.append({'date': day, 'count': len(rows), 'gap_days': days_between(previous_day, day) if previous_day else None})
        previous_day = day
    for e in all_events:
        e['gaps'] = gaps_of(e['spans'])
        e.setdefault('removed_after_gap', False)
    return all_events, history


def end_date_changes(all_events, history):
    """How many current notices changed their estimated end date between two captures that are not separated by a gap.

    Only notices still on the list in the latest capture are counted (`removed_on` is None). A change is the first
    capture that shows a new end date; it counts only when the capture before it is at most MAX_GAP_DAYS earlier,
    because across a longer gap the date may have changed at any time and that is not observed (scripts/gaps.py).
    A notice counts once, however many times its date changed. The text of the site says "in our captures": a change
    before the first capture, or one that was undone between two captures, is not seen.
    """
    days = [h['date'] for h in history]
    before = {day: days[i - 1] for i, day in enumerate(days) if i}
    current = [e for e in all_events if not e['removed_on']]
    changed = sum(any(not is_gap(before[c['seen']], c['seen']) for c in e['end_changes'][1:]) for e in current)
    return {'current': len(current), 'changed': changed, 'from': days[0], 'to': days[-1], 'max_gap_days': MAX_GAP_DAYS}


def load_snapshots():
    """Own daily snapshots, plus imported captures for dates they do not cover."""
    folder = ROOT / 'data/snapshots'
    own = {p.stem: p for p in folder.glob('????-??-??.txt')}
    earlier = {p.stem: p for p in (folder / 'imported').glob('????-??-??.txt') if p.stem not in own}
    paths = {**earlier, **own}
    return [(day, read_snapshot(paths[day])) for day in sorted(paths)], set(earlier)


def read_triage_counts():
    path = ROOT / 'data/triage-counts.json'
    return json.loads(path.read_text(encoding='utf-8'))['counts'] if path.exists() else []


def group_lists(current, members, current_vnrs, day=None):
    """{group: {'available': [...], 'short': [...]}} for the groups of current shortages: the other packages on the market,
    split into those a pharmacy can usually give (triage.is_available_alternative, the rule that sets the impact level) and those that are short too.
    Small, so it goes with the medicine pages."""
    day = day or helsinki_today()
    def item(p):
        return {k: p[k] for k in ('vnr', 'name', 'strength', 'pack_label', 'company')}
    def listed(p):
        return bool(({p['vnr']} | p['old']) & current_vnrs)
    out = {}
    for g in sorted({e['substitution_group'] for e in current if e.get('substitution_group')}):
        packs = sorted((p for p in members.get(g, []) if p['market'] == '1'), key=lambda p: (p['name'].casefold(), p['strength'], p['pack']))
        out[g] = {'available': [item(p) for p in packs if is_available_alternative(p, current_vnrs, day, True)],
                  'short': [dict(item(p), listed=listed(p)) for p in packs if listed(p) or p['short']]}
    return out


def critical_events(snapshots, members, products, register_date=None):
    """Newly critical groups, newest first, with names for people: the medicine, its strength and the packages listed."""
    out = []
    for ev in newly_critical(snapshots, members, register_date):
        listed = [dict(vnr=v, **{k: products.get(v, {}).get(k, '') for k in ('name', 'strength', 'substances', 'form', 'pack_label')}) for v in ev['vnrs']]
        first = next((x for x in listed if x['name']), {})
        out.append(dict(ev, medicine=medicine_name(first.get('substances', '')) or first.get('name', ''), strength=first.get('strength', ''), form=first.get('form', ''),
                        packages=[{k: x[k] for k in ('vnr', 'name', 'strength', 'pack_label')} for x in listed]))
    return sorted(out, key=lambda x: (x['date'], x['group']), reverse=True)


def read_rss_counts():
    path = ROOT / 'data/snapshots/imported/rss-counts.json'
    return json.loads(path.read_text(encoding='utf-8'))['captures'] if path.exists() else []


def build():
    snapshots, imported = load_snapshots()
    if not snapshots:
        raise ValueError('No snapshots')
    es, history = events(snapshots)
    for h in history:
        h['imported'] = h['date'] in imported
    current_vnrs = {e['NordicArticleNumber'] for e in es if e['removed_on'] is None}
    members = {}
    details = {}
    names = {'trade': Counter(), 'substances': Counter(), 'strengths': {}}
    products = register(ROOT / 'data/source/register.xml', {e['NordicArticleNumber'] for e in es}, current_vnrs, members, details, None, names)
    search_words = {}
    for e in es:
        e.update(products.get(e['NordicArticleNumber'], {}))
        # Finnish substance words for the search; kept only in current.json and removed.json, so the other files stay as they were.
        if e.get('substance_fi') is not None:
            search_words[e['NordicArticleNumber']] = e.pop('substance_fi')
        if e['removed_on'] is None:
            e.setdefault('other_packages_count', 0)
            e['impact'] = level(e)
            e['medicine'] = medicine_name(e.get('substances', ''))
        else:
            e.pop('other_packages_count', None)
    current = [e for e in es if e['removed_on'] is None]
    unmatched = sorted({e['NordicArticleNumber'] for e in current if not e.get('name')})
    matched = sum(bool(e.get('name')) for e in current)
    if matched * 100 < len(current) * 95:
        raise ValueError(f'Register matched only {matched} of {len(current)} current rows')
    metadata_path = ROOT / 'data/source/metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.exists() else {}
    register_metadata = ROOT / 'data/source/register-metadata.json'
    if register_metadata.exists():
        metadata.update(json.loads(register_metadata.read_text(encoding='utf-8')))
    metadata['source_credit'] = fimea_credit(metadata)
    # The register's own run date: the history reads the register's flags only for the capture of that day.
    register_path = ROOT / 'data/source/register.xml'
    critical = critical_events(snapshots, members, products, metadata.get('register_date') or (register_date(register_path) if register_path.exists() else None))
    # One page for each verified group of register packages (scripts/medicine_pages.py); it puts `medicine_page` on the notices of its packages.
    shard_meta = {'archive_start': history[0]['date'], 'snapshot_date': history[-1]['date'], 'source_metadata': metadata, 'generated_at': datetime.now(timezone.utc).isoformat(), 'last_checked': os.environ.get('LAST_CHECKED') or None}
    medicine_dir = ROOT / 'site/m'
    # Without a register file (tests that replace `register`) there are no groups and no pages.
    medicine_counts = build_pages(register_path, register_date(register_path), current_vnrs, es, shard_meta, medicine_dir) if register_path.exists() else {}
    output = {'archive_start': history[0]['date'], 'snapshot_date': history[-1]['date'], 'history': history, 'events': es, 'unmatched_vnrs': unmatched, 'end_changes': end_date_changes(es, history), 'rss_counts': read_rss_counts(), 'max_gap_days': MAX_GAP_DAYS, 'source_metadata': metadata,
              'newly_critical': critical, 'triage_counts': read_triage_counts()}
    output['generated_at'] = shard_meta['generated_at']
    output['last_checked'] = shard_meta['last_checked']
    csv_columns = ['VNR', 'current VNR', 'name', 'strength', 'form', 'pack', 'active substances', 'ATC', 'company', 'start date', 'estimated end date', 'notification date', 'veterinary', 'other packages on market', 'substitution group', 'impact', 'source credit']
    with (ROOT / 'site/shortages.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(csv_columns)
        for e in current:
            writer.writerow([e['NordicArticleNumber'], e.get('current_vnr', ''), e.get('name', ''), e.get('strength', ''), e.get('form', ''), e.get('pack', ''), e.get('substances', ''), e.get('atc', ''), e['Company'], e['UnavailableFrom'], e['EndingDate'], e['DateOfTheNotification'], 'yes' if e.get('atc', '').startswith('Q') else 'no' if e.get('atc') else '', e.get('other_packages_count', 0) if e.get('substitution_group') else '', e.get('substitution_group', ''), e['impact'], metadata['source_credit']])
    (ROOT / 'site/data.json').write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    current_data = {k: output[k] for k in ('archive_start', 'snapshot_date', 'source_metadata', 'generated_at', 'last_checked')}
    current_data['events'] = [dict(e, substance_fi=search_words[e['NordicArticleNumber']]) if search_words.get(e['NordicArticleNumber']) else e for e in current]
    history_data = {k: output[k] for k in ('history', 'end_changes', 'rss_counts', 'max_gap_days', 'newly_critical', 'triage_counts')}
    history_data['source_metadata'] = metadata
    history_data['first_capture_count'] = sum(bool(e.get('listed_at_first_capture')) for e in es)
    for name, value in [('current.json', current_data), ('history.json', history_data)]:
        (ROOT / 'site' / name).write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    meta = {k: output[k] for k in ('archive_start', 'snapshot_date', 'source_metadata', 'generated_at', 'last_checked')}
    # The name index of the home page: every register name, so a name that was never short is not answered with "not found".
    (ROOT / 'site/names.json').write_text(json.dumps(name_index(names, metadata.get('register_date') or ''), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    # The pages that load no other data (the EU list pages, 404) read this for the freshness banner and footer, from the same build.
    (ROOT / 'site/source.json').write_text(json.dumps(meta, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    shard_dir = ROOT / 'site/p'
    shard_dir.mkdir(exist_ok=True)
    for name, shard in package_shards(es, meta, group_lists(current, members, current_vnrs)).items():
        (shard_dir / f'{name}.json').write_text(json.dumps(shard, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    (ROOT / 'site/removed.json').write_text(json.dumps(dict(meta, events=[dict(r, substance_fi=search_words[r['NordicArticleNumber']]) if search_words.get(r['NordicArticleNumber']) else r for r in removed_index(es)]), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    home = summary(current, meta)
    (ROOT / 'site/summary.json').write_text(json.dumps(home, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    (ROOT / 'site/week.json').write_text(json.dumps(week_file(week_summary(es, snapshots, history), metadata), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    for name, text in feeds(es, snapshots, history, critical).items():
        (ROOT / 'site' / name).write_text(text, encoding='utf-8', newline='\n')
    eu = eu_list.load_eu_list()
    matches = eu_list.match_all(es, products, details, eu, eu_list.load_routes(), eu_list.load_forms(), eu_list.load_ingredient_rules())
    rows = eu_list.current_rows(es, matches)
    alerts = eu_list.new_alerts(es, matches, snapshots, _shift(history[-1]['date'], eu_list.ALERT_DAYS))
    eu_list.write_outputs(ROOT / 'site', rows, eu['meta'], metadata, history[-1]['date'], alerts)
    critical_data = {'substance_fi': search_words, 'eu': eu, 'rows': rows, 'counts': eu_list.counts(rows), 'history': eu_list.history(es, matches, [d for d, _ in snapshots]), 'archive_start': history[0]['date'], 'snapshot_date': history[-1]['date'], 'source_metadata': metadata}
    for name, html in render_pages(home['short_now'], home['impact'], critical_data, home['expected_soon'], home['snapshot_date']).items():
        (ROOT / 'site' / name).write_text(html, encoding='utf-8', newline='\n')
    print(f"rows={len(current)} matched_names={sum(bool(e.get('name')) for e in current)} unmatched_vnrs={len(unmatched)} impact={home['impact']} newly_critical={len(critical)} eu_list={eu_list.counts(rows)} eu_alerts={len(alerts)} medicine_pages={medicine_counts}")


if __name__ == '__main__':
    build()
