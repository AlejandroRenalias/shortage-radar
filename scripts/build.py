"""Build a static dataset from Fimea snapshots and its basic register."""
import csv
import json
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
import os
import unicodedata
from statistics import median
from pathlib import Path

import critical as eu_list
from changes import _shift, feeds, week_summary
from packs import pack_label
from pages import render_pages
from slices import package_shards, summary
from triage import level, medicine_name, newly_critical

ROOT = Path(__file__).resolve().parents[1]
# Captures further apart than this are not joined into one continuous series,
# and removal windows or first sightings wider than this are not used for delays.
MAX_GAP_DAYS = 14
MIN_DELAY_SAMPLE = 30
# Product fields kept out of the shortage events: the holder, and the route and flag details the critical medicines join reads.
PRIVATE = {'holder', 'routes', 'eu_flag', 'form_id'}
HEADER = ['NordicArticleNumber', 'Valid', 'UnavailableFrom', 'EndingDate', 'DateOfTheNotification', 'Updated', 'Company']


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


def register(path, wanted, current_shortages=(), members=None, details=None):
    """Register details for the wanted VNRs, with the count of other packages in the same substitution group that are
    on the market, not flagged short in the register and not in the current shortage file.

    When `members` is a dict, it is filled with {group: [package]} for every package with a substitution group, for the
    history of the groups and for the list of alternatives on the medicine page.
    When `details` is a dict, it is filled with {vnr: {'routes', 'eu_flag', 'form_id', 'substances'}} for the wanted VNRs:
    what the critical medicines join needs and the other pages do not.
    """
    packages, exact, products, substances = {}, set(), {}, {}
    candidates = []
    current_shortages = set(current_shortages)
    for _, el in ET.iterparse(path, events=('end',)):
        if el.tag == 'Pakkaus':
            vnr = el.findtext('VNR-numero')
            unit = el.find('Pakkauskokoyksikko')
            package = (el.get('Laakevalmiste-ref'), [x.get('Laakeaine-ref') for x in el.findall('Pakkaus_Laakeaine')], el.findtext('Pakkauskokoteksti', ''), vnr or '', unit.get('value', '') if unit is not None else '')
            old_vnrs = {x.text for x in el.findall('VanhaVNR') if x.text}
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
            products[el.get('id')] = {'routes': routes, 'eu_flag': (el.findtext('EUKriittinenValmiste') or '').strip(), 'form_id': form.get('id', '') if form is not None else '', 'name': el.findtext('Kauppanimi', ''), 'strength': el.findtext('Vahvuus', ''), 'form': form.get('value', '') if form is not None else '', 'atc': atc.get('id', '') if atc is not None else '', 'substitution_group': group.get('value', '') if group is not None else '', 'holder': el.findtext('Myyntilupa/Haltija', '')}
            el.clear()
        elif el.tag == 'Laakeaine':
            substances[el.get('id')] = [x.get('value', '') for x in el.findall('./VaikuttavaAine/Aine')]
            el.clear()
    available = {}
    for ref, vnr, old_vnrs, market, shortage, entry, exit_, pack, unit in candidates:
        product = products.get(ref, {})
        key = group_key(product)
        if key and vnr and market == '1' and shortage == '0' and not ({vnr} | old_vnrs) & current_shortages:
            available.setdefault(key, set()).add(vnr)
        if key and vnr and members is not None:
            members.setdefault(key, []).append({'vnr': vnr, 'old': old_vnrs, 'market': market, 'short': shortage == '1', 'entry': entry, 'exit': exit_,
                                                'name': product['name'], 'strength': product['strength'], 'pack': pack, 'pack_label': pack_label(pack, unit, product['form']), 'company': product['holder']})
    result = {}
    for vnr, (ref, refs, pack, current_vnr, unit) in packages.items():
        if ref in products:
            product = {k: v for k, v in products[ref].items() if k not in PRIVATE}
            key = group_key(product)
            count = len(available.get(key, set()) - {vnr, current_vnr}) if key else 0
            names = list(dict.fromkeys(s for r in refs for s in substances.get(r, []) if s))
            result[vnr] = dict(product, current_vnr=current_vnr, pack=pack, pack_label=pack_label(pack, unit, product['form']), substances=', '.join(names), other_packages_count=count)
            if details is not None:
                details[vnr] = dict({k: products[ref][k] for k in ('routes', 'eu_flag', 'form_id')}, substances=names)
    return result


def days_between(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def events(snapshots):
    """Track events across captures.

    Captures are days or weeks apart, so every start and end is a window:
    an event began after `first_seen_after` (None for the first capture) and
    no later than `first_seen`; it ended after `last_seen` and no later than
    `removed_on` (None while still listed).
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
                e = dict(row, first_seen=day, first_seen_after=previous_day, listed_at_first_capture=previous_day is None, last_seen=day, first_estimated_end=row['EndingDate'], end_changes=[{'seen': day, 'date': row['EndingDate']}], removed_on=None)
                active[key] = e
                all_events.append(e)
            else:
                e = active[key]
                if e['EndingDate'] != row['EndingDate']:
                    e['end_changes'].append({'seen': day, 'date': row['EndingDate']})
                e.update(row, last_seen=day)
        listed = {key[0] for key in seen}
        for key in set(active) - seen:
            e = active.pop(key)
            # A changed start date or notification date shows up as a removal plus a new event.
            e.update(removed_on=day, vnr_listed_at_removal=key[0] in listed)
        history.append({'date': day, 'count': len(rows), 'gap_days': days_between(previous_day, day) if previous_day else None})
        previous_day = day
    return all_events, history


def delay_stats(all_events):
    """Compare the first estimated end with the window in which the record left the list.

    Only events with a narrow window at both ends are used: first seen within
    MAX_GAP_DAYS of the previous capture (so the first estimate is close to the
    original one) and removed within MAX_GAP_DAYS of the last capture listing it.
    """
    sample, active_past, excluded = [], [], {'listed_at_first_capture': 0, 'no_estimate': 0, 'wide_start_window': 0, 'wide_removal_window': 0, 'vnr_still_listed': 0}
    for e in all_events:
        end = e.get('first_estimated_end')
        if not e['removed_on']:
            if (end and not e['listed_at_first_capture'] and e['first_seen_after']
                    and days_between(e['first_seen_after'], e['first_seen']) <= MAX_GAP_DAYS
                    and days_between(end, e['last_seen']) > 0):
                active_past.append(days_between(end, e['last_seen']))
            continue
        if e['listed_at_first_capture']:
            reason = 'listed_at_first_capture'
        elif not end:
            reason = 'no_estimate'
        elif days_between(e['first_seen_after'], e['first_seen']) > MAX_GAP_DAYS:
            reason = 'wide_start_window'
        elif days_between(e['last_seen'], e['removed_on']) > MAX_GAP_DAYS:
            reason = 'wide_removal_window'
        elif e.get('vnr_listed_at_removal'):
            reason = 'vnr_still_listed'
        else:
            reason = None
        if reason:
            excluded[reason] += 1
            continue
        low, high = days_between(end, e['last_seen']), days_between(end, e['removed_on'])
        sample.append({'vnr': e['NordicArticleNumber'], 'name': e.get('name', ''), 'strength': e.get('strength', ''), 'first_estimated_end': end, 'last_seen': e['last_seen'], 'removed_on': e['removed_on'], 'overrun_min_days': low, 'overrun_max_days': high})
    past = [s for s in sample if s['overrun_min_days'] > 0]
    not_past = [s for s in sample if s['overrun_max_days'] <= 0]
    result = {'sample_size': len(sample), 'past_estimate': len(past), 'not_past_estimate': len(not_past), 'undetermined': len(sample) - len(past) - len(not_past), 'active_past_estimate': len(active_past), 'excluded': excluded, 'removed_total': len(sample) + sum(excluded.values()), 'min_sample': MIN_DELAY_SAMPLE, 'max_gap_days': MAX_GAP_DAYS, 'meaningful': len(sample) >= MIN_DELAY_SAMPLE, 'examples': sorted(past, key=lambda s: -s['overrun_min_days'])[:10]}
    if result['meaningful']:
        result['share_past_min'] = len(past) / len(sample)
        result['share_past_max'] = (len(sample) - len(not_past)) / len(sample)
    if past:
        result['median_overrun_min_days'] = median(s['overrun_min_days'] for s in past)
        result['median_overrun_max_days'] = median(s['overrun_max_days'] for s in past)
    return result


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


def group_lists(current, members, current_vnrs):
    """{group: {'available': [...], 'short': [...]}} for the groups of current shortages: the other packages on the market,
    split into those a pharmacy can usually give and those that are short too. Small, so it goes with the medicine pages."""
    def item(p):
        return {k: p[k] for k in ('vnr', 'name', 'strength', 'pack_label', 'company')}
    def listed(p):
        return bool(({p['vnr']} | p['old']) & current_vnrs)
    out = {}
    for g in sorted({e['substitution_group'] for e in current if e.get('substitution_group')}):
        packs = sorted((p for p in members.get(g, []) if p['market'] == '1'), key=lambda p: (p['name'].casefold(), p['strength'], p['pack']))
        out[g] = {'available': [item(p) for p in packs if not listed(p) and not p['short']],
                  'short': [dict(item(p), listed=listed(p)) for p in packs if listed(p) or p['short']]}
    return out


def critical_events(snapshots, members, products):
    """Newly critical groups, newest first, with names for people: the medicine, its strength and the packages listed."""
    out = []
    for ev in newly_critical(snapshots, members):
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
    products = register(ROOT / 'data/source/register.xml', {e['NordicArticleNumber'] for e in es}, current_vnrs, members, details)
    for e in es:
        e.update(products.get(e['NordicArticleNumber'], {}))
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
    critical = critical_events(snapshots, members, products)
    output = {'archive_start': history[0]['date'], 'snapshot_date': history[-1]['date'], 'history': history, 'events': es, 'unmatched_vnrs': unmatched, 'delays': delay_stats(es), 'rss_counts': read_rss_counts(), 'max_gap_days': MAX_GAP_DAYS, 'source_metadata': metadata,
              'newly_critical': critical, 'triage_counts': read_triage_counts()}
    output['generated_at'] = datetime.now(timezone.utc).isoformat()
    output['last_checked'] = os.environ.get('LAST_CHECKED') or None
    csv_columns = ['VNR', 'current VNR', 'name', 'strength', 'form', 'pack', 'active substances', 'ATC', 'company', 'start date', 'estimated end date', 'notification date', 'veterinary', 'other packages on market', 'substitution group', 'impact']
    with (ROOT / 'site/shortages.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(csv_columns)
        for e in current:
            writer.writerow([e['NordicArticleNumber'], e.get('current_vnr', ''), e.get('name', ''), e.get('strength', ''), e.get('form', ''), e.get('pack', ''), e.get('substances', ''), e.get('atc', ''), e['Company'], e['UnavailableFrom'], e['EndingDate'], e['DateOfTheNotification'], 'yes' if e.get('atc', '').startswith('Q') else 'no' if e.get('atc') else '', e.get('other_packages_count', 0) if e.get('substitution_group') else '', e.get('substitution_group', ''), e['impact']])
    (ROOT / 'site/data.json').write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    current_data = {k: output[k] for k in ('archive_start', 'snapshot_date', 'source_metadata', 'generated_at', 'last_checked')}
    current_data['events'] = current
    history_data = {k: output[k] for k in ('history', 'delays', 'rss_counts', 'max_gap_days', 'newly_critical', 'triage_counts')}
    history_data['first_capture_count'] = sum(bool(e.get('listed_at_first_capture')) for e in es)
    for name, value in [('current.json', current_data), ('history.json', history_data)]:
        (ROOT / 'site' / name).write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    meta = {k: output[k] for k in ('archive_start', 'snapshot_date', 'source_metadata', 'generated_at', 'last_checked')}
    shard_dir = ROOT / 'site/p'
    shard_dir.mkdir(exist_ok=True)
    for name, shard in package_shards(es, meta, group_lists(current, members, current_vnrs)).items():
        (shard_dir / f'{name}.json').write_text(json.dumps(shard, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    home = summary(current, meta)
    (ROOT / 'site/summary.json').write_text(json.dumps(home, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    (ROOT / 'site/week.json').write_text(json.dumps(week_summary(es, snapshots, history), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    for name, text in feeds(es, snapshots, history, critical).items():
        (ROOT / 'site' / name).write_text(text, encoding='utf-8', newline='\n')
    eu = eu_list.load_eu_list()
    matches = eu_list.match_all(es, products, details, eu, eu_list.load_routes(), eu_list.load_forms(), eu_list.load_ingredient_rules())
    rows = eu_list.current_rows(es, matches)
    alerts = eu_list.new_alerts(es, matches, snapshots, _shift(history[-1]['date'], eu_list.ALERT_DAYS))
    eu_list.write_outputs(ROOT / 'site', rows, eu['meta'], metadata, history[-1]['date'], alerts)
    critical_data = {'eu': eu, 'rows': rows, 'counts': eu_list.counts(rows), 'history': eu_list.history(es, matches, [d for d, _ in snapshots]), 'archive_start': history[0]['date'], 'snapshot_date': history[-1]['date'], 'source_metadata': metadata}
    for name, html in render_pages(len(current), home['impact'], critical_data).items():
        (ROOT / 'site' / name).write_text(html, encoding='utf-8', newline='\n')
    print(f"rows={len(current)} matched_names={sum(bool(e.get('name')) for e in current)} unmatched_vnrs={len(unmatched)} impact={home['impact']} newly_critical={len(critical)} eu_list={eu_list.counts(rows)} eu_alerts={len(alerts)}")


if __name__ == '__main__':
    build()
