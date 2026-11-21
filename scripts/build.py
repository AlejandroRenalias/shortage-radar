"""Build a static dataset from Fimea snapshots and its basic register."""
import csv
import json
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def events(snapshots):
    active, all_events, history = {}, [], []
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
                e = dict(row, first_seen=day, last_seen=day, first_estimated_end=row['EndingDate'], end_changes=[{'seen': day, 'date': row['EndingDate']}], removed_on=None)
                active[key] = e
                all_events.append(e)
            else:
                e = active[key]
                if e['EndingDate'] != row['EndingDate']:
                    e['end_changes'].append({'seen': day, 'date': row['EndingDate']})
                e.update(row, last_seen=day)
        for key in set(active) - seen:
            active.pop(key)['removed_on'] = day
        history.append({'date': day, 'count': len(rows)})
    return all_events, history


def build():
    paths = sorted((ROOT / 'data/snapshots').glob('????-??-??.txt'))
    if not paths:
        raise ValueError('No snapshots')
    snapshots = [(p.stem, read_snapshot(p)) for p in paths]
    es, history = events(snapshots)
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
    output = {'archive_start': history[0]['date'], 'snapshot_date': history[-1]['date'], 'history': history, 'events': es, 'unmatched_vnrs': unmatched, 'source_metadata': metadata}
    (ROOT / 'site/data.json').write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f"rows={len(current)} matched_names={sum(bool(e.get('name')) for e in current)} unmatched_vnrs={len(unmatched)}")


if __name__ == '__main__':
    build()
