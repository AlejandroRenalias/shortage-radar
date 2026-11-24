"""Medicine pages: one page for each verified group of register packages (docs/medicine-groups-spec.md).

A group gets a page only when the audit says `first_release_candidate`: no unsure reason, one product record, one known container.
A package in any other group keeps its package page only. The page lists the packages of the group that have a shortage notice
in the archive (current or past). Each package keeps its own notices, its own source and its own history.

What the page may say is bound by the page contract in the spec: the group says that the register fields are equal and nothing else.
No substitute claim, no stock claim, no history of the group. Fimea's substitution code and the impact label stay out of the page data.

The page reads `m/<id>.json`. The same build puts `medicine_page: <id>` on every notice of a listed package, so the search can link to it.
A notice joined to the register only by an old VNR is not placed: the page lists packages by their current VNR.
"""
import json

from audit_groups import group_lookup, group_packages, read_register

# Event fields that belong to the package page, not to a medicine page: Fimea's substitution code and our impact label built on it.
NOT_FOR_MEDICINE_PAGE = ('substitution_group', 'other_packages_count', 'impact')
META_KEYS = ('archive_start', 'snapshot_date', 'source_metadata', 'generated_at', 'last_checked')


def verified_groups(packages, day, listed):
    """The groups that get a medicine page: audit `first_release_candidate` groups, with every group considered for the VNR join."""
    groups = group_packages(packages, day, listed)
    return [g for g in groups if g['first_release_candidate']], groups


def attach(events, verified, every_group):
    """Set `medicine_page` on each notice whose VNR is the current VNR of a package in a verified group. Returns {group id: group}.

    A VNR on two register records is not placed (group_lookup), and such a group is unsure anyway. A notice whose VNR is only an old VNR
    of a register package is left without a page: the register can give an old VNR to more than one package."""
    ids = {g['id'] for g in verified}
    where = group_lookup(every_group)
    pages = {}
    for e in events:
        g = where.get(e['NordicArticleNumber'])
        if g and g['id'] in ids:
            e['medicine_page'] = g['id']
            pages[g['id']] = g
    return pages


def page_data(group, events, meta):
    """The data file of one medicine page: the register fields the group shares (inputs of the rule) and, for each package with a notice,
    its own notices as the package page has them."""
    inputs = group['inputs']
    presentation = inputs.get('presentation') or {}
    mine = [e for e in events if e.get('medicine_page') == group['id']]
    first = sorted(mine, key=lambda e: (e['NordicArticleNumber'], e.get('removed_on') or '9999', e['first_seen']))[0]
    by_vnr = {}
    for e in mine:
        by_vnr.setdefault(e['NordicArticleNumber'], []).append({k: v for k, v in e.items() if k not in NOT_FOR_MEDICINE_PAGE and k != 'medicine_page'})
    packages = []
    for vnr in sorted(by_vnr, key=lambda v: (by_vnr[v][0].get('pack_label', {}).get('en', ''), v)):
        # Current notices first, then ended ones, the most recently seen first.
        notices = sorted(sorted(sorted(by_vnr[vnr], key=lambda e: e['first_seen']), key=lambda e: e['last_seen'], reverse=True), key=lambda e: e.get('removed_on') is not None)
        packages.append({'vnr': vnr, 'events': notices})
    return dict({k: meta[k] for k in META_KEYS}, id=group['id'], medicine={
        'name': first.get('name', ''), 'strength': first.get('strength', ''), 'substances': [s[1] for s in inputs['substances']],
        'form': inputs['form'][1], 'routes': [r[1] for r in inputs['routes']], 'atc': inputs['atc'],
        'container': (presentation.get('container') or ['', ''])[1], 'unit_size': presentation.get('unit_size', ''),
        'device': inputs['device'][1],
    }, packages=packages)


def build_pages(register_path, day, listed, events, meta, folder):
    """Read the register, attach the pages to the notices and write one data file for each page. Returns a count summary."""
    packages = read_register(register_path)
    verified, every_group = verified_groups(packages, day, listed)
    pages = attach(events, verified, every_group)
    folder.mkdir(exist_ok=True)
    for old in folder.glob('m*.json'):
        old.unlink()
    for gid, group in pages.items():
        (folder / f'{gid}.json').write_text(json.dumps(page_data(group, events, meta), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    placed = {e['NordicArticleNumber'] for e in events if e.get('medicine_page')}
    return {'verified_groups': len(verified), 'pages': len(pages), 'packages_on_pages': len(placed),
            'single_package_pages': sum(1 for gid in pages if len({e['NordicArticleNumber'] for e in events if e.get('medicine_page') == gid}) == 1)}
