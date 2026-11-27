"""Group pages: one page for each substitution group that has at least one package on Fimea's shortage list (site/group.html?g=<code>).

One source of truth. `classify` is the only place that decides, for the register packages of one group, which are on the shortage list
and which are interchangeable packages found in the data (`triage.is_available_alternative`, the rule that sets `other_packages_count`
and `impact`). The medicine page lists (`build.group_lists`) and the group page data (`group_shards`) both read its result, so no page
can count alternatives in another way. `alternatives` of a group page is the length of the same list; for every listed package of the
group it equals the `other_packages_count` of that package in current.json (tests/test_group_pages.py checks it on the real build).

The page reads `g/NN.json`, where NN is the last two digits of the group code (every one of the 100 files exists, as with `p/NN.json`).
A group without a listed package is not in any file: the page then says that no package of the group is on the list, and nothing more.
Packages without a group (`nogroup`) never get a page. The page is for today only: it holds no history.
"""
import re
from collections import Counter

from triage import is_available_alternative, medicine_name

META_KEYS = ('archive_start', 'snapshot_date', 'source_metadata', 'generated_at', 'last_checked')


def shard_name(code):
    return code[-2:]


def on_list(p, current_vnrs):
    """A register package is on the shortage list when its VNR or one of its old VNRs is in the current shortage file."""
    return bool(({p['vnr']} | p['old']) & current_vnrs)


def classify(members, current_vnrs, day):
    """[(package, on the shortage list, interchangeable package found in the data)] for the register packages of one group that are
    on the market (`Kaupan` 1) or on the list, in a stable order: name, strength, pack. The third value is `is_available_alternative`
    with the register day's flags, exactly the check the impact level uses."""
    ordered = sorted(members, key=lambda p: (p['name'].casefold(), p['strength'], p['pack']))
    out = []
    for p in ordered:
        listed = on_list(p, current_vnrs)
        if p['market'] == '1' or listed:
            out.append((p, listed, is_available_alternative(p, current_vnrs, day, True)))
    return out


def heading(rows):
    """The words of the page title: active substance, strength and form, from the register. They come from the packages on the shortage list
    (the register lists excipients as substances of some other packages, which would give a wrong title). A group can write its strength or
    form in different ways; the most common spelling among those packages wins, then alphabetical order."""
    count = Counter()
    for p, _, _ in [r for r in rows if r[1]] or rows:
        # medicine_name keeps the "hydrogen" of a salt such as "Rivastigmine hydrogen tartrate"; it is not part of the name of a medicine.
        name = ' '.join(re.sub(r'(?<=\w) hydrogen\b', '', medicine_name(p.get('substances', ''))).split())
        count[(name or p['name'], p['strength'], p.get('form', ''))] += 1
    substance, strength, form = sorted(count, key=lambda k: (-count[k], k))[0]
    return {'substance': substance, 'strength': strength, 'form': form}


def group_page(rows, has_page):
    """The data of one group page, from `classify`'s rows. `has_page` is the set of VNRs that have a package page (a notice, current or past)."""
    alt = [p for p, _, a in rows if a]
    companies = sorted({p['company'] for p in alt if p['company']}, key=str.casefold)
    packages = []
    for p, listed, a in sorted(rows, key=lambda r: not r[1]):  # listed first; sorted() is stable, so the order inside each part stays
        link = next((v for v in [p['vnr'], *sorted(p['old'])] if v in has_page), '')
        packages.append({'vnr': p['vnr'], 'name': p['name'], 'strength': p['strength'], 'pack_label': p['pack_label'], 'company': p['company'],
                         'listed': listed, 'alt': a, 'link': link})
    return {'heading': heading(rows),
            'counts': {'market': sum(p['market'] == '1' for p, _, _ in rows), 'listed': sum(listed for _, listed, _ in rows), 'alternatives': len(alt), 'companies': len(companies)},
            'alt_companies': companies, 'packages': packages}


def group_shards(codes, members, current_vnrs, day, has_page, meta):
    """{'00': {...meta, 'groups': {code: page}}, ..., '99': ...} for the groups in `codes` (the groups of the packages on the list today)."""
    shards = {f'{n:02d}': dict({k: meta[k] for k in META_KEYS}, groups={}) for n in range(100)}
    for code in sorted(codes):
        rows = classify(members.get(code, []), current_vnrs, day)
        if any(listed for _, listed, _ in rows):
            shards[shard_name(code)]['groups'][code] = group_page(rows, has_page)
    return shards
