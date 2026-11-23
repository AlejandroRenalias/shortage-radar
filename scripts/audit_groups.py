"""Audit of the "same medicine" grouping rule (docs/medicine-groups-spec.md). Nothing on the site uses it yet.

Reads the whole basic register in one streaming pass, joins the current shortage file, builds the groups and writes
data/audit/groups.json, data/audit/summary.json and data/audit/summary.md. The output is deterministic: the same register and
the same shortage file give the same bytes. The day used is the register's own run date (`Ajopvm`), not the clock.

    python scripts/audit_groups.py [register.xml] [shortage snapshot.txt]

The grouping function is `group_packages`; it takes plain dicts, so tests can build small registers by hand.
"""
import hashlib
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from triage import is_available_alternative, on_market

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/audit'
# Why a group is "unsure": no medicine page, the packages stay package pages. See docs/medicine-groups-spec.md.
REASONS = (
    'veterinary', 'no_marketing_authorisation_record', 'no_substance_listed', 'strength_not_stated', 'route_not_stated',
    'product_substances_inconsistent', 'register_group_disagrees', 'several_products_no_register_group', 'biological_several_products', 'vnr_listed_twice',
)
FLAGS = ('merges_different_substance', 'merges_different_strength', 'merges_different_form', 'merges_different_route')
_NUMBER = re.compile(r'\d+(?:[.,]\d+)?')


def normalise_strength(text):
    """The strength text of a product (`Vahvuus`) in one spelling: case, spaces and the decimal separator are made equal,
    numbers lose trailing zeros ("0,50 mg" and "0.5 MG" are the same). Units are not converted: "500 mikrog" and "0.5 mg" stay different."""
    text = unicodedata.normalize('NFKC', text or '').casefold()

    def number(match):
        try:
            return format(Decimal(match.group().replace(',', '.')).normalize(), 'f')
        except InvalidOperation:
            return match.group()
    return ' '.join(_NUMBER.sub(number, text).split())


def rule_inputs(p):
    """What decides that two packages are the same medicine. Two packages with equal inputs are in one group; any difference splits them."""
    return {
        'species': 'vet' if p['vet'] else 'human',
        'target_species': sorted(p.get('target_species') or []),
        'substances': sorted({(s['id'], s['name']) for s in p['substances']}),
        'strength': normalise_strength(p['strength']),
        'form': (p['form_id'], p['form']),
        'routes': sorted({(r[0], r[1]) for r in p['routes']}),
        'atc': p['atc'],
        'device': p.get('device') or ['', ''],
    }


def group_id(inputs):
    return 'm' + hashlib.sha1(json.dumps(inputs, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:12]


def parallel_kind(p):
    """'import', 'distribution' or '' from the product's marketing authorisation flags."""
    return 'import' if p.get('parallel_import') == '1' else 'distribution' if p.get('parallel_distribution') == '1' else ''


def group_packages(packages, day=None, listed=()):
    """Group register packages (dicts, see `read_register`) into medicines. Returns a list of group dicts sorted by id.

    The checks that compare the register's substitution group codes and the marketing authorisations look at the current members only:
    packages on the market on `day` (`triage.on_market`) and packages in the shortage file `listed`. A package long off the market
    does not make a group unsure. With no `day`, every member is current. A group with no current member is judged on all its members.

    Each group has `id`, `inputs` (rule_inputs), `vnrs` (sorted), the four `merges_different_*` flags (always false when the rule works:
    they are checked again on the raw fields of the members), `unsure` and `unsure_reasons`, and facts about its members.
    """
    listed = set(listed)
    members = defaultdict(list)
    inputs_of = {}
    for p in packages:
        inputs = rule_inputs(p)
        gid = group_id(inputs)
        inputs_of[gid] = inputs
        members[gid].append(p)
    # A product whose packages list different substances in the register is a data conflict: all its packages are unsure.
    by_product = defaultdict(set)
    for p in packages:
        by_product[p['product']].add(tuple(sorted({s['id'] for s in p['substances']})))
    inconsistent = {ref for ref, sets in by_product.items() if len(sets) > 1}
    # A VNR on two register packages (a package entered again under a new product) cannot be placed with certainty.
    twice = {v for v, n in Counter(p['vnr'] for p in packages).items() if n > 1}
    out = []
    for gid in sorted(members):
        ps = sorted(members[gid], key=lambda p: p['vnr'])
        inputs = inputs_of[gid]
        reasons = set()
        if any(p['vet'] for p in ps):
            reasons.add('veterinary')
        if not all(p['licensed'] for p in ps):
            reasons.add('no_marketing_authorisation_record')
        if not inputs['substances']:
            reasons.add('no_substance_listed')
        if not inputs['strength']:
            reasons.add('strength_not_stated')
        if not inputs['routes']:
            reasons.add('route_not_stated')
        if any(p['vnr'] in twice for p in ps):
            reasons.add('vnr_listed_twice')
        if any(p['product'] in inconsistent for p in ps):
            reasons.add('product_substances_inconsistent')
        current = [p for p in ps if day is None or on_market(p, day) or ({p['vnr']} | set(p['old'])) & listed] or ps
        codes = {p['substitution_group'] for p in current}
        if len(codes) > 1:
            reasons.add('register_group_disagrees')
        # Own authorisations, not counting parallel imports and distributions of them.
        own = {p['authorisation'] for p in current if not parallel_kind(p)}
        if len(own) > 1:
            if codes == {''}:
                reasons.add('several_products_no_register_group')
            if any(p['biological'] or p['plasma'] for p in current):
                reasons.add('biological_several_products')
        raw = {
            'merges_different_substance': len({tuple(sorted({s['id'] for s in p['substances']})) for p in ps}) > 1,
            'merges_different_strength': len({normalise_strength(p['strength']) for p in ps}) > 1,
            'merges_different_form': len({p['form_id'] for p in ps}) > 1,
            'merges_different_route': len({tuple(sorted({r[0] for r in p['routes']})) for p in ps}) > 1,
        }
        out.append(dict(
            id=gid, inputs=inputs, vnrs=[p['vnr'] for p in ps], **raw,
            unsure=bool(reasons), unsure_reasons=sorted(reasons),
            names=sorted({p['name'] for p in ps}), register_groups=sorted({p['substitution_group'] for p in ps if p['substitution_group']}), current_members=len(current),
            products=len({p['product'] for p in ps}), authorisations=len({p['authorisation'] for p in ps}),
            parallel_import=sorted(p['vnr'] for p in ps if parallel_kind(p) == 'import'),
            parallel_distribution=sorted(p['vnr'] for p in ps if parallel_kind(p) == 'distribution'),
        ))
    return out


def read_register(path):
    """Every register package as a dict, in file order. The register is read once, element by element."""
    products, substances, packs = {}, {}, []
    for _, el in ET.iterparse(path, events=('end',)):
        if el.tag == 'Pakkaus':
            unit = el.find('Pakkauskokoyksikko')
            device = el.find('Annostelulaite')
            packs.append({
                'product': el.get('Laakevalmiste-ref'), 'vnr': el.findtext('VNR-numero') or '',
                'old': sorted({x.text for x in el.findall('VanhaVNR') if x.text}),
                'substance_refs': [x.get('Laakeaine-ref') for x in el.findall('Pakkaus_Laakeaine')],
                'market': el.findtext('Kaupanolo/Kaupan'), 'entry': el.findtext('Kaupanolo/Kauppaantulopaiva') or '',
                'exit': el.findtext('Kaupanolo/Kaupastapoistumispaiva') or '', 'shortage_flag': el.findtext('SaatavuushairioTiedot/Saatavuushairio'),
                'pack': el.findtext('Pakkauskokoteksti', ''), 'unit': unit.get('value', '') if unit is not None else '',
                'device': [device.get('id', ''), device.get('value', '')] if device is not None and device.get('id') else None,
            })
            el.clear()
        elif el.tag == 'Laakevalmiste':
            atc, form, group = el.find('ATC-koodi'), el.find('Laakemuoto'), el.find('Substituutioryhma')
            licence = el.find('Myyntilupa')
            products[el.get('id')] = {
                'name': el.findtext('Kauppanimi', ''), 'atc': atc.get('id', '') if atc is not None else '',
                'strength': (el.findtext('Vahvuus') or '').strip(),
                'form_id': form.get('id', '') if form is not None else '', 'form': form.get('value', '') if form is not None else '',
                'routes': [(x.get('id', ''), x.get('value', '')) for x in el.findall('Antoreitti')],
                'substitution_group': group.get('value', '') if group is not None else '',
                'vet': el.findtext('VET') == '1' or (atc is not None and atc.get('id', '').startswith('Q')),
                'target_species': [x.find('Elainlaji').get('value', '') for x in el.findall('Kohdeelainlaji') if x.find('Elainlaji') is not None],
                'biological': el.findtext('Biologinen') == '1', 'plasma': el.findtext('Plasmaperainenvalmiste') == '1',
                'licensed': licence is not None, 'authorisation': (licence.findtext('Lupanumero') or '').strip() if licence is not None else '',
                'holder': licence.findtext('Haltija', '') if licence is not None else '',
                'parallel_import': licence.findtext('RinnakkaisTuonti') if licence is not None else '',
                'parallel_distribution': licence.findtext('RinnakkaisJakelu') if licence is not None else '',
            }
            el.clear()
        elif el.tag == 'Laakeaine':
            substances[el.get('id')] = sorted({(x.find('Aine').get('id', ''), x.find('Aine').get('value', '')) for x in el.findall('VaikuttavaAine') if x.find('Aine') is not None})
            el.clear()
    out = []
    for pk in packs:
        product = products.get(pk['product'])
        if product is None or not pk['vnr']:
            continue
        names = sorted({s for r in pk['substance_refs'] for s in substances.get(r, [])})
        out.append(dict(product, **{k: pk[k] for k in ('product', 'vnr', 'old', 'market', 'entry', 'exit', 'shortage_flag', 'pack', 'unit', 'device')},
                        substances=[{'id': i, 'name': n} for i, n in names]))
    return out


def current_shortage_vnrs(path):
    """VNRs of the shortage file at `path` (the same reader as the build)."""
    from build import read_snapshot
    return {r['NordicArticleNumber'] for r in read_snapshot(Path(path))}


def shortage_packages(packages, listed):
    """{shortage VNR: package} by the current VNR, else an old VNR (the build joins the same way)."""
    by_vnr = {p['vnr']: p for p in packages}
    old = {}
    for p in packages:
        for v in p['old']:
            old.setdefault(v, p)
    return {v: by_vnr.get(v) or old.get(v) for v in sorted(listed)}


def summarise(groups, packages, listed, day):
    """The numbers of the audit. `listed` is the current shortage file's VNR set."""
    by_vnr = {p['vnr']: p for p in packages}
    group_of = {v: g for g in groups for v in g['vnrs']}
    matched = shortage_packages(packages, listed)
    in_shortage_groups = {group_of[p['vnr']]['id'] for p in matched.values() if p}
    on_market_ids = {g['id'] for g in groups if any(on_market(by_vnr[v], day) for v in g['vnrs'])}
    sets = {'all': {g['id'] for g in groups}, 'on_market': on_market_ids, 'in_current_shortage': in_shortage_groups}
    by_id = {g['id']: g for g in groups}
    out = {'register_day': day, 'packages': len(packages), 'groups': len(groups), 'shortage_vnrs': len(listed),
           'shortage_vnrs_found_in_register': sum(1 for p in matched.values() if p), 'scopes': {}}
    for name, ids in sets.items():
        gs = [by_id[i] for i in sorted(ids)]
        reasons = Counter(r for g in gs for r in g['unsure_reasons'])
        out['scopes'][name] = {
            'groups': len(gs), 'unsure_groups': sum(g['unsure'] for g in gs), 'unsure_reasons': dict(sorted(reasons.items())),
            'single_package_groups': sum(len(g['vnrs']) == 1 for g in gs),
            'groups_with_several_active_substances': sum(len(g['inputs']['substances']) > 1 for g in gs),
            'groups_with_parallel_import': sum(bool(g['parallel_import']) for g in gs),
            'groups_with_parallel_distribution': sum(bool(g['parallel_distribution']) for g in gs),
            **{flag: [g['id'] for g in gs if g[flag]] for flag in FLAGS},
        }
    return out


def register_group_comparison(groups, packages):
    """How the register's own substitution groups (the rule the site uses today) relate to these groups.

    For every register group code with more than one medicine group: which of substance, strength, form, route and device differ.
    """
    package_group = {v: g for g in groups for v in g['vnrs']}
    by_code = defaultdict(set)
    for p in packages:
        if p['substitution_group']:
            by_code[p['substitution_group']].add(package_group[p['vnr']]['id'])
    by_id = {g['id']: g for g in groups}
    spans = Counter()
    split = 0
    for code, ids in by_code.items():
        if len(ids) < 2:
            continue
        split += 1
        gs = [by_id[i]['inputs'] for i in ids]
        for key in ('substances', 'strength', 'form', 'routes', 'device', 'atc'):
            if len({json.dumps(x[key]) for x in gs}) > 1:
                spans[key] += 1
    return {'register_groups': len(by_code), 'register_groups_spanning_several_medicine_groups': split,
            'differences_among_those': dict(sorted(spans.items()))}


def alternative_comparison(groups, packages, listed, day):
    """For each current shortage: the alternatives by the register group (today's rule, `is_available_alternative`) and by the medicine group."""
    by_vnr = {p['vnr']: p for p in packages}
    group_of = {v: g for g in groups for v in g['vnrs']}
    members = defaultdict(list)
    for p in packages:
        if p['substitution_group']:
            members[p['substitution_group']].append({'vnr': p['vnr'], 'old': set(p['old']), 'market': p['market'], 'shortage_flag': p['shortage_flag'], 'entry': p['entry'], 'exit': p['exit']})

    def count(candidates, own):
        return sum(1 for m in candidates if m['vnr'] != own and is_available_alternative(m, listed, day, True))
    table = Counter()
    for v, p in shortage_packages(packages, listed).items():
        if not p or p['vet']:
            continue
        g = group_of[p['vnr']]
        register = count(members[p['substitution_group']], p['vnr']) if p['substitution_group'] else None
        mine = None if g['unsure'] else count([{'vnr': x, 'old': set(by_vnr[x]['old']), 'market': by_vnr[x]['market'], 'shortage_flag': by_vnr[x]['shortage_flag'],
                                                'entry': by_vnr[x]['entry'], 'exit': by_vnr[x]['exit']} for x in g['vnrs']], p['vnr'])
        table[('no_register_group' if register is None else 'register_alt' if register else 'register_none',
               'unsure' if mine is None else 'group_alt' if mine else 'group_none')] += 1
    return {f'{a} / {b}': n for (a, b), n in sorted(table.items())}


def examples(groups, listed):
    """15 example groups of different kinds, chosen by group id from the groups that have a package in the current shortage file.
    Returns [(kind, [group, ...])]; a kind that keeps groups apart shows the two groups that differ in one input only."""
    here = [g for g in groups if set(g['vnrs']) & set(listed)]
    sure = [g for g in here if not g['unsure']]
    out = []

    def take(kind, found, n):
        out.extend((kind, [g]) for g in found[:n])

    take('one substance', [g for g in sure if len(g['inputs']['substances']) == 1 and len(g['vnrs']) >= 4 and not g['parallel_import']], 3)
    take('combination product', [g for g in sure if len(g['inputs']['substances']) >= 2 and len(g['vnrs']) >= 2], 3)
    take('parallel import joined to the original', [g for g in sure if g['parallel_import'] and len(g['vnrs']) >= 3], 3)
    for kind, drop in (('different strengths kept apart', 'strength'), ('different forms kept apart', 'form'), ('different routes kept apart', 'routes')):
        buckets = defaultdict(list)
        for g in sure:
            buckets[json.dumps({k: v for k, v in g['inputs'].items() if k != drop}, sort_keys=True)].append(g)
        pairs = [sorted(b, key=lambda g: g['id'])[:2] for _, b in sorted(buckets.items()) if len(b) > 1]
        out.extend((kind, pair) for pair in pairs[:2 if drop == 'strength' else 1])
    for reason in ('register_group_disagrees', 'strength_not_stated'):
        found = [g for g in here if g['inputs']['species'] == 'human' and reason in g['unsure_reasons']]
        take(f'unsure: {reason}', sorted(found, key=lambda g: (len(g['unsure_reasons']), g['id'])), 1)
    return out


def examples_text(found):
    lines = ['# Example groups', '', 'Chosen by group id from the groups with a package in the current shortage file. Facts from the register only.', '']
    for n, (kind, gs) in enumerate(found, 1):
        lines.append(f'## {n}. {kind}')
        lines.append('')
        for g in gs:
            i = g['inputs']
            lines.append(f"- `{g['id']}`: {' + '.join(s[1] for s in i['substances']) or '(none listed)'}; strength {i['strength'] or '(not stated)'}; form {i['form'][1]}; "
                         f"route {', '.join(r[1] for r in i['routes']) or '(not stated)'}; ATC {i['atc']}; names {', '.join(g['names'][:5])}")
            lines.append(f"  - VNRs: {', '.join(g['vnrs'][:12])}{' ...' if len(g['vnrs']) > 12 else ''} ({len(g['vnrs'])} packages)")
            if g['parallel_import']:
                lines.append(f"  - parallel import VNRs: {', '.join(g['parallel_import'][:8])}")
            lines.append(f"  - {'unsure: ' + ', '.join(g['unsure_reasons']) if g['unsure'] else 'not unsure'}")
        lines.append('')
    return '\n'.join(lines)


def write(groups, summary, folder=OUT):
    folder.mkdir(parents=True, exist_ok=True)
    lines = ',\n'.join(json.dumps(g, ensure_ascii=False, separators=(',', ':')) for g in groups)
    (folder / 'groups.json').write_text('[\n' + lines + '\n]\n', encoding='utf-8', newline='\n')
    (folder / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    (folder / 'summary.md').write_text(summary_text(summary), encoding='utf-8', newline='\n')


def summary_text(s):
    lines = [f"# Medicine groups audit, register of {s['register_day']}", '',
             f"{s['packages']} register packages in {s['groups']} groups. {s['shortage_vnrs']} VNRs in the current shortage file, {s['shortage_vnrs_found_in_register']} found in the register.", '']
    for name, scope in s['scopes'].items():
        lines += [f"## {name.replace('_', ' ')}: {scope['groups']} groups", '',
                  f"- unsure: {scope['unsure_groups']}",
                  *[f'  - {r}: {n}' for r, n in scope['unsure_reasons'].items()],
                  f"- single-package groups: {scope['single_package_groups']}",
                  f"- groups with several active substances: {scope['groups_with_several_active_substances']}",
                  f"- groups with a parallel import: {scope['groups_with_parallel_import']}; with a parallel distribution: {scope['groups_with_parallel_distribution']}",
                  *[f"- {flag}: {len(scope[flag])}" for flag in FLAGS], '']
    lines += ['## Register substitution groups against these groups', '', '```', json.dumps(s['register_groups'], indent=1), '```', '',
              '## Current shortages: alternatives by register group / by medicine group (human medicines)', '', '```', json.dumps(s['alternatives'], indent=1), '```', '']
    return '\n'.join(lines)


def main(register=None, shortages=None):
    register = Path(register or ROOT / 'data/source/register.xml')
    shortages = Path(shortages or sorted((ROOT / 'data/snapshots').glob('*.txt'))[-1])
    packages = read_register(register)
    from source_age import register_date
    day = register_date(register)
    listed = current_shortage_vnrs(shortages)
    groups = group_packages(packages, day, listed)
    summary = summarise(groups, packages, listed, day)
    summary['shortage_file'] = shortages.name
    summary['register_groups'] = register_group_comparison(groups, packages)
    summary['alternatives'] = alternative_comparison(groups, packages, listed, day)
    write(groups, summary)
    (OUT / 'examples.md').write_text(examples_text(examples(groups, listed)), encoding='utf-8', newline='\n')
    print(summary_text(summary))


if __name__ == '__main__':
    main(*sys.argv[1:3])
