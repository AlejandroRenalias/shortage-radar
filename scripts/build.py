"""Build a static dataset from Fimea snapshots and its basic register."""
import csv
import json
import xml.etree.ElementTree as ET
from datetime import date
from statistics import median
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Captures further apart than this are not joined into one continuous series,
# and removal windows or first sightings wider than this are not used for delays.
MAX_GAP_DAYS = 14
MIN_DELAY_SAMPLE = 30
HEADER = ['NordicArticleNumber', 'Valid', 'UnavailableFrom', 'EndingDate', 'DateOfTheNotification', 'Updated', 'Company']


def read_snapshot(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, delimiter=';', strict=True)
        if reader.fieldnames != HEADER:
            raise ValueError(f'{path}: unexpected header')
        rows = list(reader)
    if not rows:
        raise ValueError(f'{path}: no rows')
    for row in rows:
        if None in row or any(row[k] is None for k in HEADER) or not row['NordicArticleNumber'].isdigit() or len(row['NordicArticleNumber']) != 6:
            raise ValueError(f'{path}: malformed row {row}')
        for k in ('UnavailableFrom', 'EndingDate', 'DateOfTheNotification', 'Updated'):
            if row[k]:
                date.fromisoformat(row[k])
    return rows


def register(path, wanted):
    packages, products, substances = {}, {}, {}
    for _, el in ET.iterparse(path, events=('end',)):
        if el.tag == 'Pakkaus':
            vnr = el.findtext('VNR-numero')
            if vnr in wanted:
                packages[vnr] = (el.get('Laakevalmiste-ref'), [x.get('Laakeaine-ref') for x in el.findall('Pakkaus_Laakeaine')], el.findtext('Pakkauskokoteksti', ''))
            el.clear()
        elif el.tag == 'Laakevalmiste':
            atc, form, group = el.find('ATC-koodi'), el.find('Laakemuoto'), el.find('Substituutioryhma')
            products[el.get('id')] = {'name': el.findtext('Kauppanimi', ''), 'strength': el.findtext('Vahvuus', ''), 'form': form.get('value', '') if form is not None else '', 'atc': atc.get('id', '') if atc is not None else '', 'substitution_group': group.get('value', '') if group is not None else ''}
            el.clear()
        elif el.tag == 'Laakeaine':
            substances[el.get('id')] = [x.get('value', '') for x in el.findall('./VaikuttavaAine/Aine')]
            el.clear()
    result = {}
    for vnr, (ref, refs, pack) in packages.items():
        if ref in products:
            result[vnr] = dict(products[ref], pack=pack, substances=', '.join(dict.fromkeys(s for r in refs for s in substances.get(r, []) if s)))
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
        sample.append({'vnr': e['NordicArticleNumber'], 'name': e.get('name', ''), 'first_estimated_end': end, 'last_seen': e['last_seen'], 'removed_on': e['removed_on'], 'overrun_min_days': low, 'overrun_max_days': high})
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
    products = register(ROOT / 'data/source/register.xml', {e['NordicArticleNumber'] for e in es})
    for e in es:
        e.update(products.get(e['NordicArticleNumber'], {}))
    current = [e for e in es if e['removed_on'] is None]
    unmatched = sorted({e['NordicArticleNumber'] for e in current if not e.get('name')})
    metadata_path = ROOT / 'data/source/metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.exists() else {}
    register_metadata = ROOT / 'data/source/register-metadata.json'
    if register_metadata.exists():
        metadata.update(json.loads(register_metadata.read_text(encoding='utf-8')))
    output = {'archive_start': history[0]['date'], 'snapshot_date': history[-1]['date'], 'history': history, 'events': es, 'unmatched_vnrs': unmatched, 'delays': delay_stats(es), 'rss_counts': read_rss_counts(), 'max_gap_days': MAX_GAP_DAYS, 'source_metadata': metadata}
    (ROOT / 'site/data.json').write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f"rows={len(current)} matched_names={sum(bool(e.get('name')) for e in current)} unmatched_vnrs={len(unmatched)}")


if __name__ == '__main__':
    build()
