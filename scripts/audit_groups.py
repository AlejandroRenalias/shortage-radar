"""Audit of the "same medicine" grouping rule (docs/medicine-groups-spec.md). Nothing on the site uses it yet.

Reads the whole basic register in one streaming pass, joins the current shortage file, builds the groups and writes
data/audit/groups.json, summary.json, summary.md and examples.md. The output is deterministic: the same register and
the same shortage file give the same bytes. The day used is the register's own run date (`Ajopvm`), not the clock.
summary.json records the file names, dates and SHA-256 of both source files and of groups.json.

    python scripts/audit_groups.py [register.xml] [shortage snapshot.txt]

The grouping function is `group_packages`; it takes plain dicts, so tests can build small registers by hand.

Wording: the counts of "same-key packages" are internal comparison counts. They say nothing about what is available or what can replace what.
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
    'product_substances_inconsistent', 'register_group_disagrees', 'several_products_no_register_group', 'biological_several_products',
    'vnr_listed_twice', 'authorisation_identity_missing', 'device_not_verified', 'presentation_not_verified', 'composition_differs', 'composition_not_verified',
    'parallel_not_linked',
)
FLAGS = ('merges_different_substance', 'merges_different_strength', 'merges_different_form', 'merges_different_route')
_NUMBER = re.compile(r'\d+(?:[.,]\d+)?')
_EU_BASE = re.compile(r'EU/\d+/\d+/\d+')
# A form name with one of these parts is a presentation with a device (pre-filled pen or syringe, cartridge, injector, inhaler, spray).
# Single-dose eye drops and "annosteltu" powders are not listed: the word "dose" alone does not name a device.
DEVICE_WORDS = ('esitäyt', 'kynä', 'ruisku', 'injektori', 'sylinteri', 'inhalaat', 'sumut', 'laite')
# An injectable form (injection or infusion) is sold in a container the register names (vial, ampoule, pre-filled syringe, bag ...).
INJECTABLE_WORDS = ('injek', 'infuusio')
MASS_MG = {'g': Decimal(1000), 'mg': Decimal(1), 'mikrog': Decimal('0.001'), 'µg': Decimal('0.001'), 'ng': Decimal('0.000001')}
# Two members' amount ratios may differ by this much (rounding in the register) before the composition counts as different.
RATIO_TOLERANCE = Decimal('0.02')
# Cases found in review. Each list of VNRs must never be in one group the audit calls sure; see tests and data/audit/examples.md.
COUNTEREXAMPLES = {
    'NovoRapid and Fiasp (two EU authorisations, biological)': ('007523', '472559'),
    'Insulin Lispro Sanofi and Liprolog (two EU authorisations, biological)': ('117084', '165713'),
    'Physioneal 35 and 40 Clear-Flex (other calcium and lactate)': ('016111', '016129', '016194'),
    'Liprolog KwikPen and Junior KwikPen (no device data)': ('517586', '544210'),
    'Rybelsus 1.5 mg and parallel-distributed Wegovy 1.5 mg': ('130247', '074190'),
    'Rybelsus 4 mg and parallel-distributed Wegovy 4 mg': ('083695', '117765'),
    'Caninda (strength text kept apart from component names)': ('110560', '450435'),
    'Trexan pre-filled syringes of 0.3 ml and 1.0 ml (one product record, no device id)': ('562071', '456852'),
    'Celeston Chronodose vial and ampoule (other immediate containers)': ('433078', '473507'),
    'VNRs with two register records (Topimax, Mirena, Haemate)': ('018486', '370212', '424765'),
}


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
    """What decides that two packages are the same medicine. Two packages with equal inputs are in one group; any difference splits them.

    `strength_text` is the product's `Vahvuus` text as the register writes it. It is not mapped to the substances: the register does not
    say which part of the text belongs to which substance, and the substances here are in the order of their register id."""
    return {
        'species': 'vet' if p['vet'] else 'human',
        'target_species': sorted(p.get('target_species') or []),
        'substances': sorted({(s['id'], s['name']) for s in p['substances']}),
        'strength_text': normalise_strength(p['strength']),
        'form': (p['form_id'], p['form']),
        'routes': sorted({(r[0], r[1]) for r in p['routes']}),
        'atc': p['atc'],
        'device': p.get('device') or ['', ''],
        **({'presentation': presentation(p)} if presentation_matters(p) else {}),
    }


def group_id(inputs):
    return 'm' + hashlib.sha1(json.dumps(inputs, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:12]


def parallel_kind(p):
    """'import', 'distribution' or '' from the product's marketing authorisation flags. The flag names a sales channel, not the original product."""
    return 'import' if p.get('parallel_import') == '1' else 'distribution' if p.get('parallel_distribution') == '1' else ''


def eu_base(p):
    """The EU authorisation without its pack suffix: "EU/1/99/119/001,008,015" is "EU/1/99/119". Text of another shape is kept whole."""
    text = (p.get('eu_authorisation') or '').strip()
    match = _EU_BASE.match(text)
    return match.group() if match else text


def licence_identity(p):
    """The authorisation a product stands on: the EU number when it has one, else the national number; '' when the register gives neither."""
    eu = eu_base(p)
    if eu:
        return 'EU:' + eu
    national = (p.get('authorisation') or '').strip()
    return 'FI:' + national if national else ''


def device_bearing(p):
    return bool(p.get('device')) or any(w in (p['form'] or '').casefold() for w in DEVICE_WORDS)


def presentation_matters(p):
    """Injectables and device-bearing forms are told apart by the immediate container and the size of one unit. A box, a blister or a tube of
    another form is not a difference of presentation."""
    return device_bearing(p) or any(w in (p['form'] or '').casefold() for w in INJECTABLE_WORDS)


def _decimal_text(text):
    return normalise_strength(text)


def unit_size(p):
    """The size of ONE unit (one vial, ampoule, syringe, pen, cartridge or bag) from `Pakkauskoko` and its unit, or '' when it is not verified.

    It is verified only when the register's pack text says exactly the same as its fields: "5 x 1 ml" or "1 ml" for size 1, unit ml.
    The pack count and the total volume are never used. A pack with an extra pack factor, or with a text that the fields do not explain, is not verified."""
    size, unit, text = (p.get('pack_size') or '').strip(), (p.get('pack_unit') or '').strip(), p.get('pack') or ''
    if not size or not unit or p.get('pack_factor'):
        return ''
    one = f'{_decimal_text(size)} {_decimal_text(unit)}'
    # The text is the unit alone or "<whole number> x <unit>". The count is read from the text, not from `Pakkauskokokerroin`, and is not kept.
    match = re.fullmatch(r'(?:\d+ x )?(.+)', _decimal_text(text))
    return one if match and match.group(1) == one else ''


def presentation(p):
    """The register's container (`Sailytysastia`) and the verified size of one unit; the size is '' when it cannot be verified."""
    container = p.get('container') or ['', '']
    return {'container': list(container), 'unit_size': unit_size(p)}


def _quantity(a):
    """(basis, amount) of one active substance in one package, or None when it is a range, empty or unreadable. Mass units are put in mg."""
    if a.get('min') or a.get('max') or not a.get('amount'):
        return None
    try:
        value = Decimal(a['amount'].replace(',', '.'))
    except InvalidOperation:
        return None
    unit = (a.get('unit') or '').casefold()
    basis = (a.get('per') or '', a.get('as_id') or '')
    if unit in MASS_MG:
        return ('mass',) + basis, value * MASS_MG[unit]
    return ((unit,) + basis, value) if unit else None


def composition_status(packages):
    """Compare what the packages hold of each active substance, apart from the strength text: 'verified', 'differs', 'incomplete' or 'not_applicable'.

    The basis of the amounts in `Laakeaine` depends on the source: the register gives the same 25 mg for pre-filled syringes of 0.3 ml and of 1.0 ml
    (Trexan), so it is neither a per-unit strength nor a pack total, and it is never used as a strength. Only the ratios between the substances of one
    package are compared: the amount of each substance is divided by the amount of the first substance (by register id). Mass units are put in mg. 'incomplete' means the register
    does not give every amount in one basis (empty, a range, another unit, an "expressed as" substance, a substance twice); no verdict is given.
    'differs' needs a person: base or salt conventions, or really other concentrations (Physioneal 35 and 40).
    """
    if len({p['vnr'] for p in packages}) < 2 or len({s['id'] for p in packages for s in p['substances']}) < 2:
        return 'not_applicable'
    vectors = []
    for p in packages:
        amounts = p.get('amounts') or []
        ids = [a['id'] for a in amounts]
        if not amounts or len(ids) != len(set(ids)) or set(ids) != {s['id'] for s in p['substances']}:
            return 'incomplete'
        quantities = {a['id']: _quantity(a) for a in amounts}
        if any(q is None for q in quantities.values()):
            return 'incomplete'
        vectors.append({i: q for i, q in quantities.items()})
    ids = sorted(vectors[0])
    if any(sorted(v) != ids or any(v[i][0] != vectors[0][i][0] for i in ids) for v in vectors) or any(v[ids[0]][1] <= 0 for v in vectors):
        return 'incomplete'
    first = {i: vectors[0][i][1] / vectors[0][ids[0]][1] for i in ids}
    for v in vectors[1:]:
        for i in ids:
            if abs(v[i][1] / v[ids[0]][1] - first[i]) > RATIO_TOLERANCE * abs(first[i]):
                return 'differs'
    return 'verified'


def container_verified(packages):
    """Eligibility guard for the first release: a group of several packages needs ALL members to have the same KNOWN immediate container id
    (`Sailytysastia`). One product record can hold a tube and a pump bottle (Zovirax cream 081243 and 081252) with no device id and equal fields.
    A blank container is not known. A group of one package has nothing to compare. This is an eligibility check only: it adds no unsure reason
    and does not change which packages are in one group."""
    if len(packages) < 2:
        return True
    containers = {(p.get('container') or [''])[0] for p in packages}
    return len(containers) == 1 and '' not in containers


def group_packages(packages, day=None, listed=()):
    """Group register packages (dicts, see `read_register`) into medicines. Returns a list of group dicts sorted by id.

    The register's substitution group codes are compared over the current members only: packages on the market on `day` (`triage.on_market`)
    and packages in the shortage file `listed`. A package long off the market does not make a group unsure because it has no code. With no `day`,
    every member is current. A group with no current member is judged on all its members. Every other check looks at all members.

    A group whose members come from more than one product record (`product`: the register's Laakevalmiste) is unsure unless the register
    backs it: every product has an authorisation identity, the current members share one register substitution code, no member is biological,
    device-bearing presentations have a device id and the composition is verified (`composition_status`). A parallel import or distribution
    joins the original only through a shared EU authorisation number; otherwise it is a group of its own, and unsure.

    Each group has `id`, `inputs` (rule_inputs), `vnrs` (sorted), the four `merges_different_*` flags (false when the rule works:
    they are checked again on the raw fields of the members), `quantity_review`, `unsure` and `unsure_reasons`, and facts about its members.
    """
    listed = set(listed)
    buckets = defaultdict(list)
    for p in packages:
        buckets[group_id(rule_inputs(p))].append(p)
    members, inputs_of, unlinked = defaultdict(list), {}, set()
    for gid, ps in buckets.items():
        inputs = rule_inputs(ps[0])
        originals = {eu_base(p) for p in ps if not parallel_kind(p)} - {''}
        for p in ps:
            if parallel_kind(p) and eu_base(p) not in originals:
                alone = dict(inputs, unlinked_parallel=p['product'])
                key = group_id(alone)
                inputs_of[key] = alone
                unlinked.add(key)
                members[key].append(p)
            else:
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
        ps = sorted(members[gid], key=lambda p: (p['vnr'], p['product']))
        inputs = inputs_of[gid]
        reasons = set()
        if any(p['vet'] for p in ps):
            reasons.add('veterinary')
        if not all(p['licensed'] for p in ps):
            reasons.add('no_marketing_authorisation_record')
        if not inputs['substances']:
            reasons.add('no_substance_listed')
        if not inputs['strength_text']:
            reasons.add('strength_not_stated')
        if not inputs['routes']:
            reasons.add('route_not_stated')
        if any(p['vnr'] in twice for p in ps):
            reasons.add('vnr_listed_twice')
        if any(p['product'] in inconsistent for p in ps):
            reasons.add('product_substances_inconsistent')
        if gid in unlinked:
            reasons.add('parallel_not_linked')
        if any(presentation_matters(p) and (not unit_size(p) or not (p.get('container') or [''])[0]) for p in ps):
            reasons.add('presentation_not_verified')
        # A device-bearing package with no device id is an unknown device variant; nothing independent in the register says it is the same one.
        if any(device_bearing(p) and not p.get('device') for p in ps):
            reasons.add('device_not_verified')
        current = [p for p in ps if day is None or on_market(p, day) or ({p['vnr']} | set(p['old'])) & listed] or ps
        codes = {p['substitution_group'] for p in current}
        products = {p['product'] for p in ps}
        composition = composition_status(ps)
        if len(codes) > 1:
            reasons.add('register_group_disagrees')
        if composition == 'differs':
            reasons.add('composition_differs')
        if len(products) > 1:
            if len({p['product'] for p in current}) > 1 and codes == {''}:
                reasons.add('several_products_no_register_group')
            if any(not licence_identity(p) for p in ps):
                reasons.add('authorisation_identity_missing')
            if any(p['biological'] or p['plasma'] for p in ps):
                reasons.add('biological_several_products')
            if composition in ('incomplete', 'differs'):
                reasons.add('composition_not_verified')
        raw = {
            'merges_different_substance': len({tuple(sorted({s['id'] for s in p['substances']})) for p in ps}) > 1,
            'merges_different_strength': len({normalise_strength(p['strength']) for p in ps}) > 1,
            'merges_different_form': len({p['form_id'] for p in ps}) > 1,
            'merges_different_route': len({tuple(sorted({r[0] for r in p['routes']})) for p in ps}) > 1,
        }
        out.append(dict(
            id=gid, inputs=inputs, vnrs=[p['vnr'] for p in ps], **raw, quantity_review=composition == 'differs', composition=composition,
            unsure=bool(reasons), unsure_reasons=sorted(reasons),
            names=sorted({p['name'] for p in ps}), register_groups=sorted({p['substitution_group'] for p in ps if p['substitution_group']}), current_members=len(current),
            products=len(products), authorisations=sorted({licence_identity(p) for p in ps} - {''}),
            parallel_import=sorted(p['vnr'] for p in ps if parallel_kind(p) == 'import'),
            parallel_distribution=sorted(p['vnr'] for p in ps if parallel_kind(p) == 'distribution'),
            container_verified=container_verified(ps),
            first_release_candidate=not reasons and len(products) == 1 and container_verified(ps),
        ))
    return out


def read_register(path):
    """Every register package (with a VNR) as a dict, in file order. The register is read once, element by element."""
    products, substances, packs = {}, {}, []
    for _, el in ET.iterparse(path, events=('end',)):
        if el.tag == 'Pakkaus':
            unit = el.find('Pakkauskokoyksikko')
            device = el.find('Annostelulaite')
            container = el.find('Sailytysastia')
            packs.append({
                'product': el.get('Laakevalmiste-ref'), 'vnr': el.findtext('VNR-numero') or '',
                'old': sorted({x.text for x in el.findall('VanhaVNR') if x.text}),
                'substance_refs': [x.get('Laakeaine-ref') for x in el.findall('Pakkaus_Laakeaine')],
                'market': el.findtext('Kaupanolo/Kaupan'), 'entry': el.findtext('Kaupanolo/Kauppaantulopaiva') or '',
                'exit': el.findtext('Kaupanolo/Kaupastapoistumispaiva') or '', 'shortage_flag': el.findtext('SaatavuushairioTiedot/Saatavuushairio'),
                'pack': el.findtext('Pakkauskokoteksti', ''), 'unit': unit.get('value', '') if unit is not None else '',
                'device': [device.get('id', ''), device.get('value', '')] if device is not None and device.get('id') else None,
                'container': [container.get('id', ''), container.get('value', '')] if container is not None and container.get('id') else None,
                'pack_count': el.findtext('Pakkauskokokerroin') or '', 'pack_size': el.findtext('Pakkauskoko') or '', 'pack_unit': unit.get('value', '') if unit is not None else '',
                'pack_factor': el.findtext('Pakkauskerroin') or '',
            })
            el.clear()
        elif el.tag == 'Laakevalmiste':
            atc, form, group = el.find('ATC-koodi'), el.find('Laakemuoto'), el.find('Substituutioryhma')
            licences = el.findall('Myyntilupa')
            national = sorted({(x.findtext('Lupanumero') or '').strip() for x in licences} - {''})
            european = sorted({(x.findtext('EU-lupanumero') or '').strip() for x in licences} - {''})
            products[el.get('id')] = {
                'name': el.findtext('Kauppanimi', ''), 'atc': atc.get('id', '') if atc is not None else '',
                'strength': (el.findtext('Vahvuus') or '').strip(),
                'form_id': form.get('id', '') if form is not None else '', 'form': form.get('value', '') if form is not None else '',
                'routes': [(x.get('id', ''), x.get('value', '')) for x in el.findall('Antoreitti')],
                'substitution_group': group.get('value', '') if group is not None else '',
                'vet': el.findtext('VET') == '1' or (atc is not None and atc.get('id', '').startswith('Q')),
                'target_species': [x.find('Elainlaji').get('value', '') for x in el.findall('Kohdeelainlaji') if x.find('Elainlaji') is not None],
                'biological': el.findtext('Biologinen') == '1', 'plasma': el.findtext('Plasmaperainenvalmiste') == '1',
                # National and EU numbers are both read. Several licence records on one product are joined with ';'.
                'licensed': bool(licences), 'authorisation': ';'.join(national), 'eu_authorisation': ';'.join(european),
                'holder': '; '.join(sorted({x.findtext('Haltija', '') for x in licences})),
                'parallel_import': '1' if any(x.findtext('RinnakkaisTuonti') == '1' for x in licences) else '0' if licences else '',
                'parallel_distribution': '1' if any(x.findtext('RinnakkaisJakelu') == '1' for x in licences) else '0' if licences else '',
            }
            el.clear()
        elif el.tag == 'Laakeaine':
            substances[el.get('id')] = [{
                'id': x.find('Aine').get('id', ''), 'name': x.find('Aine').get('value', ''), 'amount': (x.findtext('Maara') or '').strip(),
                'unit': x.find('Maarayksikko').get('value', '') if x.find('Maarayksikko') is not None else '',
                'min': (x.findtext('MaaraMin') or '').strip(), 'max': (x.findtext('MaaraMax') or '').strip(), 'per': (x.findtext('VastatenMaara') or '').strip(),
                'as_id': x.find('VastatenAine').get('id', '') if x.find('VastatenAine') is not None else '',
            } for x in el.findall('VaikuttavaAine') if x.find('Aine') is not None]
            el.clear()
    out = []
    for pk in packs:
        product = products.get(pk['product'])
        if product is None or not pk['vnr']:
            continue
        amounts = [a for r in pk['substance_refs'] for a in substances.get(r, [])]
        names = sorted({(a['id'], a['name']) for a in amounts})
        out.append(dict(product, **{k: pk[k] for k in ('product', 'vnr', 'old', 'market', 'entry', 'exit', 'shortage_flag', 'pack', 'unit', 'device', 'container', 'pack_count', 'pack_size', 'pack_unit', 'pack_factor')},
                        substances=[{'id': i, 'name': n} for i, n in names], amounts=amounts))
    return out


def current_shortage_vnrs(path):
    """VNRs of the shortage file at `path` (the same reader as the build)."""
    from build import read_snapshot
    return {r['NordicArticleNumber'] for r in read_snapshot(Path(path))}


def on_market_now(p, day):
    """On the market on the register's day: the register flag `Kaupan` is 1 and the market dates agree. The dates alone are an estimate."""
    return p['market'] == '1' and on_market(p, day)


def shortage_join(packages, listed):
    """How the shortage VNRs meet the register: {'matched': {vnr: package}, 'ambiguous': [vnr], 'unmatched': [vnr], 'by_old_vnr': [vnr]}.

    A VNR is joined by the current VNR, else by an old VNR (the build joins the same way). A VNR on more than one register package is
    ambiguous: no package is chosen for it and it is left out of every count that needs a group.
    """
    current = defaultdict(list)
    old = defaultdict(list)
    for p in packages:
        current[p['vnr']].append(p)
        for v in p['old']:
            old[v].append(p)
    out = {'matched': {}, 'ambiguous': [], 'unmatched': [], 'by_old_vnr': []}
    for v in sorted(listed):
        found, via_old = current.get(v), False
        if not found:
            found, via_old = old.get(v), True
        if not found:
            out['unmatched'].append(v)
        elif len({p['product'] for p in found}) > 1 or len(found) > 1:
            out['ambiguous'].append(v)
        else:
            out['matched'][v] = found[0]
            if via_old:
                out['by_old_vnr'].append(v)
    return out


def group_lookup(groups):
    """{vnr: group} for VNRs that are in exactly one group; a VNR on two register records is not placed."""
    seen = defaultdict(list)
    for g in groups:
        for v in g['vnrs']:
            seen[v].append(g)
    return {v: gs[0] for v, gs in seen.items() if len(gs) == 1}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def source_facts(register, shortages):
    """Exact names, dates and hashes of the inputs, from the files and from data/source metadata."""
    facts = {'register_file': register.name, 'register_sha256': sha256(register), 'register_bytes': register.stat().st_size,
             'shortage_file': shortages.name, 'shortage_sha256': sha256(shortages), 'shortage_bytes': shortages.stat().st_size, 'shortage_snapshot_date': shortages.stem}
    for name, keys in (('register-metadata.json', ('register_file', 'register_date', 'register_last_modified')), ('metadata.json', ('shortages_last_modified', 'snapshot_date'))):
        path = register.parent / name
        if path.exists():
            meta = json.loads(path.read_text(encoding='utf-8'))
            facts.update({('register_source_name' if k == 'register_file' else k): meta.get(k) for k in keys})
    return facts


def summarise(groups, packages, listed, day):
    """The numbers of the audit. `listed` is the current shortage file's VNR set."""
    join = shortage_join(packages, listed)
    where = group_lookup(groups)
    by_id = {g['id']: g for g in groups}
    by_vnr = defaultdict(list)
    for p in packages:
        by_vnr[p['vnr']].append(p)
    twice = sorted(v for v, ps in by_vnr.items() if len(ps) > 1)
    in_shortage = {where[p['vnr']]['id'] for p in join['matched'].values() if p['vnr'] in where}
    strict = {where[p['vnr']]['id'] for p in packages if p['vnr'] in where and on_market_now(p, day)}
    dates_only = sorted({p['vnr'] for p in packages if on_market(p, day) and p['market'] != '1'})
    sets = {'all': {g['id'] for g in groups}, 'on_market': strict, 'in_current_shortage': in_shortage}
    out = {'register_day': day, 'packages': len(packages), 'groups': len(groups),
           'shortage_vnrs': len(listed), 'shortage_vnrs_confident': len(join['matched']), 'shortage_vnrs_ambiguous': join['ambiguous'],
           'shortage_vnrs_unmatched': join['unmatched'], 'shortage_vnrs_joined_by_old_vnr': join['by_old_vnr'],
           'register_vnrs_on_two_records': twice,
           'on_market_definition': 'register flag Kaupan is 1 and the market entry and exit dates agree',
           'packages_on_market_by_dates_only': dates_only, 'scopes': {}}
    for name, ids in sets.items():
        gs = [by_id[i] for i in sorted(ids)]
        reasons = Counter(r for g in gs for r in g['unsure_reasons'])
        out['scopes'][name] = {
            'groups': len(gs), 'unsure_groups': sum(g['unsure'] for g in gs), 'unsure_reasons': dict(sorted(reasons.items())),
            'first_release_candidates': sum(g['first_release_candidate'] for g in gs),
            'container_guard_only': sum(not g['unsure'] and g['products'] == 1 and not g['container_verified'] for g in gs),
            'single_package_groups': sum(len(g['vnrs']) == 1 for g in gs),
            'groups_with_several_active_substances': sum(len(g['inputs']['substances']) > 1 for g in gs),
            'groups_with_parallel_import': sum(bool(g['parallel_import']) for g in gs),
            'groups_with_parallel_distribution': sum(bool(g['parallel_distribution']) for g in gs),
            'groups_with_quantity_review': sum(g['quantity_review'] for g in gs),
            **{flag: [g['id'] for g in gs if g[flag]] for flag in FLAGS},
        }
    return out


def register_group_comparison(groups, packages):
    """How the register's own substitution groups relate to these groups.

    For every register group code with more than one medicine group: which of substance, strength text, form, route, device and ATC differ.
    """
    where = group_lookup(groups)
    by_code = defaultdict(set)
    for p in packages:
        if p['substitution_group'] and p['vnr'] in where:
            by_code[p['substitution_group']].add(where[p['vnr']]['id'])
    by_id = {g['id']: g for g in groups}
    spans = Counter()
    split = 0
    for code, ids in by_code.items():
        if len(ids) < 2:
            continue
        split += 1
        gs = [by_id[i]['inputs'] for i in ids]
        for key in ('substances', 'strength_text', 'form', 'routes', 'device', 'atc', 'presentation'):
            if len({json.dumps(x.get(key)) for x in gs}) > 1:
                spans[key] += 1
    return {'register_groups': len(by_code), 'register_groups_spanning_several_medicine_groups': split,
            'differences_among_those': dict(sorted(spans.items()))}


def same_key_comparison(groups, packages, listed, day):
    """For each current shortage of a human medicine: other packages found by the register code (the rule of `is_available_alternative`) against
    other packages found in the same group. Internal comparison counts only. VNRs on two records, and packages in unsure groups, are counted apart."""
    where = group_lookup(groups)
    records = {p['vnr']: p for p in packages}
    members = defaultdict(list)
    for p in packages:
        members[p['substitution_group']].append(p)

    def card(p):
        return {'vnr': p['vnr'], 'old': set(p['old']), 'market': p['market'], 'shortage_flag': p['shortage_flag'], 'entry': p['entry'], 'exit': p['exit']}

    def count(candidates, own):
        return sum(1 for m in candidates if m['vnr'] != own and is_available_alternative(card(m), listed, day, True))
    table = Counter()
    join = shortage_join(packages, listed)
    for v, p in join['matched'].items():
        if p['vet'] or p['vnr'] not in where:
            continue
        g = where[p['vnr']]
        register = count(members[p['substitution_group']], p['vnr']) if p['substitution_group'] else None
        mine = None if g['unsure'] else count([records[x] for x in g['vnrs']], p['vnr'])
        table[('no_register_code' if register is None else 'other_package_listed' if register else 'none',
               'unsure_group' if mine is None else 'other_package_listed' if mine else 'none')] += 1
    return {f'register code: {a}; same-key group: {b}': n for (a, b), n in sorted(table.items())}


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
    take('parallel import joined by an EU authorisation', [g for g in sure if g['parallel_import'] or g['parallel_distribution']], 2)
    take('unsure: parallel import without a source-backed link', [g for g in here if 'parallel_not_linked' in g['unsure_reasons']], 1)
    for kind, drop in (('different strengths kept apart', 'strength_text'), ('different forms kept apart', 'form'), ('different routes kept apart', 'routes')):
        buckets = defaultdict(list)
        for g in sure:
            buckets[json.dumps({k: v for k, v in g['inputs'].items() if k != drop}, sort_keys=True)].append(g)
        pairs = [sorted(b, key=lambda g: g['id'])[:2] for _, b in sorted(buckets.items()) if len(b) > 1]
        out.extend((kind, pair) for pair in pairs[:2 if drop == 'strength_text' else 1])
    for reason in ('register_group_disagrees', 'strength_not_stated', 'composition_not_verified'):
        found = [g for g in here if g['inputs']['species'] == 'human' and reason in g['unsure_reasons']]
        take(f'unsure: {reason}', sorted(found, key=lambda g: (len(g['unsure_reasons']), g['id'])), 1)
    return out


def _describe(g):
    i = g['inputs']
    return (f"- `{g['id']}`: {' + '.join(s[1] for s in i['substances']) or '(none listed)'} (substances in register id order); "
            f"strength text from the register: \"{i['strength_text'] or '(not stated)'}\", not mapped to the substances; form {i['form'][1]}; "
            f"route {', '.join(r[1] for r in i['routes']) or '(not stated)'}; ATC {i['atc']}; names {', '.join(g['names'][:5])}\n"
            f"  - VNRs: {', '.join(g['vnrs'][:12])}{' ...' if len(g['vnrs']) > 12 else ''} ({len(g['vnrs'])} packages, {g['products']} product records)\n"
            f"  - authorisations: {', '.join(g['authorisations']) or '(none)'}; composition check: {g['composition']}\n"
            + (f"  - parallel import VNRs: {', '.join(g['parallel_import'][:8])}; parallel distribution VNRs: {', '.join(g['parallel_distribution'][:8])}\n" if g['parallel_import'] or g['parallel_distribution'] else '')
            + f"  - {'unsure: ' + ', '.join(g['unsure_reasons']) if g['unsure'] else 'not unsure'}")


def examples_text(found, counterexamples=()):
    lines = ['# Example groups', '', 'Chosen by group id from the groups with a package in the current shortage file. Facts from the register only.', '']
    for n, (kind, gs) in enumerate(found, 1):
        lines += [f'## {n}. {kind}', '', *[_describe(g) for g in gs], '']
    if counterexamples:
        lines += ['# Cases from the review', '', 'Each case must be unsure, or kept in separate groups. The groups here are the ones that hold these VNRs.', '']
        for label, gs in counterexamples:
            lines += [f'## {label}', '', *[_describe(g) for g in gs], '']
    return '\n'.join(lines)


def counterexample_groups(groups):
    where = defaultdict(list)
    for g in groups:
        for v in g['vnrs']:
            where[v].append(g)
    return [(label, sorted({g['id']: g for v in vnrs for g in where.get(v, [])}.values(), key=lambda g: g['id'])) for label, vnrs in COUNTEREXAMPLES.items()]


def write(groups, summary, folder=OUT):
    folder.mkdir(parents=True, exist_ok=True)
    lines = ',\n'.join(json.dumps(g, ensure_ascii=False, separators=(',', ':')) for g in groups)
    (folder / 'groups.json').write_text('[\n' + lines + '\n]\n', encoding='utf-8', newline='\n')
    summary['sources']['groups_json_sha256'] = sha256(folder / 'groups.json')
    (folder / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    (folder / 'summary.md').write_text(summary_text(summary), encoding='utf-8', newline='\n')


def summary_text(s):
    src = s.get('sources', {})
    lines = [f"# Medicine groups audit, register of {s['register_day']}", '']
    if src:
        lines += ['## Sources', '', *[f'- {k}: {v}' for k, v in src.items()], '']
    lines += [f"{s['packages']} register packages with a VNR in {s['groups']} groups. {s['shortage_vnrs']} VNRs in the current shortage file: "
              f"{s['shortage_vnrs_confident']} joined to one register package, {len(s['shortage_vnrs_ambiguous'])} ambiguous (on two register records: {', '.join(s['shortage_vnrs_ambiguous']) or 'none'}), "
              f"{len(s['shortage_vnrs_unmatched'])} not found. {len(s['shortage_vnrs_joined_by_old_vnr'])} joined by an old VNR.", '',
              f"Register VNRs on two records: {len(s['register_vnrs_on_two_records'])}. On the market means: {s['on_market_definition']}. "
              f"Packages that the market dates put on the market while the flag is not 1: {len(s['packages_on_market_by_dates_only'])} ({', '.join(s['packages_on_market_by_dates_only'])}); they are not counted.", '']
    for name, scope in s['scopes'].items():
        lines += [f"## {name.replace('_', ' ')}: {scope['groups']} groups", '',
                  f"- unsure: {scope['unsure_groups']}",
                  *[f'  - {r}: {n}' for r, n in scope['unsure_reasons'].items()],
                  f"- first-release candidates (not unsure, one product record, one known container): {scope['first_release_candidates']}",
                  f"- groups kept out of the first release only by the container guard: {scope['container_guard_only']}",
                  f"- single-package groups: {scope['single_package_groups']}",
                  f"- groups with several active substances: {scope['groups_with_several_active_substances']}",
                  f"- groups with a parallel import: {scope['groups_with_parallel_import']}; with a parallel distribution: {scope['groups_with_parallel_distribution']}",
                  f"- groups flagged for quantity review: {scope['groups_with_quantity_review']}",
                  *[f"- {flag}: {len(scope[flag])}" for flag in FLAGS], '']
    lines += ['## Register substitution groups against these groups', '', '```', json.dumps(s['register_groups'], indent=1), '```', '',
              '## Current shortages of human medicines: other packages by register code against the same-key group', '',
              'Internal comparison counts. They are not availability claims and say nothing about what can replace what.', '', '```', json.dumps(s['same_key'], indent=1), '```', '']
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
    summary['sources'] = source_facts(register, shortages)
    summary['register_groups'] = register_group_comparison(groups, packages)
    summary['same_key'] = same_key_comparison(groups, packages, listed, day)
    write(groups, summary)
    (OUT / 'examples.md').write_text(examples_text(examples(groups, listed), counterexample_groups(groups)), encoding='utf-8', newline='\n')
    print(summary_text(summary))


if __name__ == '__main__':
    main(*sys.argv[1:3])
