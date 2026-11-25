"""Impact triage: can a pharmacy usually give a substitute for a package in shortage?

Each current shortage gets one level, from Fimea's substitution group (vaihtokelpoisuusryhmä) in the
basic register:

- `substitute`: the group has other packages that the register lists as on the market and not short,
  and that are not in the current shortage file. A pharmacy can usually offer one of them.
- `no_alternative`: the package has a group, but no other package in it is on the market without a shortage.
  (Named `critical` until the release that introduced `no_alternative`; `critical` is still read and written as an alias, see ALIASES.)
- `nogroup`: the package has no substitution group, so a pharmacy cannot change it on its own.
- `vet`: a veterinary medicine (ATC starting with Q). Substitution groups are for human medicines.

The register is current only, so the history of "newly critical" groups is rebuilt from the shortage
captures with today's group membership and the market dates the register gives for each package.
"""
from gaps import is_gap

LEVELS = ('substitute', 'no_alternative', 'nogroup', 'vet')
# The old name of a level, still accepted when reading and still written next to the new key in counts. Remove after one release.
ALIASES = {'critical': 'no_alternative'}
MAX_NAMED_SUBSTANCES = 2
# A group must be without alternatives in this many consecutive captures before it counts as newly critical,
# and must have had an alternative in as many captures before, so a one-capture glitch does not make an event.
CONFIRM_CAPTURES = 2
# Captures further apart than MAX_GAP_DAYS (scripts/gaps.py) do not tell when a change happened.
# Words for salts, esters and water of crystallisation at the end of a substance name: "Quetiapine fumarate" is shown as "Quetiapine".
SALT_WORDS = {
    'hydrochloride', 'dihydrochloride', 'hydrobromide', 'sodium', 'disodium', 'potassium', 'calcium', 'magnesium',
    'monohydrate', 'dihydrate', 'trihydrate', 'hemihydrate', 'sesquihydrate', 'hydrate', 'anhydrous',
    'acetate', 'tartrate', 'ditartrate', 'bitartrate', 'sulfate', 'sulphate', 'succinate', 'fumarate', 'maleate',
    'phosphate', 'bromide', 'citrate', 'besilate', 'besylate', 'mesilate', 'mesylate', 'tosilate', 'trometamol',
    'furoate', 'propionate', 'dipropionate', 'xinafoate', 'embonate', 'hyclate', 'disoproxil', 'cilexetil', 'etexilate',
}


def level(e):
    """The impact level of one current shortage (a dict with `atc`, `substitution_group` and `other_packages_count`)."""
    if (e.get('atc') or '').startswith('Q'):
        return 'vet'
    if not e.get('substitution_group'):
        return 'nogroup'
    return 'substitute' if e.get('other_packages_count', 0) > 0 else 'no_alternative'


def canonical_impact(value):
    """The current name of an impact level: the old `critical` is `no_alternative`. Ledger rows written before the rename keep the old name, so every
    history query that reads old `impact` values must pass them through this one function (ledger.read_rows does) before it compares or counts them."""
    return ALIASES.get(value, value)


def counts(current):
    out = dict.fromkeys(LEVELS, 0)
    for e in current:
        out[canonical_impact(e.get('impact') or level(e))] += 1
    return out


def with_aliases(c):
    """`counts` plus the old key for each renamed level, for the files that readers of the old name still use (summary.json, triage-counts.json)."""
    return dict(c, **{old: c[new] for old, new in ALIASES.items()})


def medicine_name(substances):
    """Active substances without salt words, for naming a medicine across its packages: "Ipratropium bromide monohydrate" -> "Ipratropium"."""
    names = []
    for part in (substances or '').split(', '):
        words = part.split()
        while len(words) > 1 and words[-1].casefold() in SALT_WORDS:
            words.pop()
        # "Sodium sulphate" stays as it is: the salt is the substance.
        if len(words) == 1 and words[0].casefold() in SALT_WORDS:
            words = part.split()
        name = ' '.join(words)
        if name and name not in names:
            names.append(name)
    # A mixture of many substances is better named by its product name.
    return ' + '.join(names) if len(names) <= MAX_NAMED_SUBSTANCES else ''


def on_market(p, day):
    """Whether a register package was on the market on `day`, from its market entry and exit dates; the market flag decides when no date is given."""
    entry, exit_ = p.get('entry') or '', p.get('exit') or ''
    if not entry:
        return p.get('market') == '1'
    if entry > day:
        return False
    # An exit before the latest entry is an earlier period off the market.
    return not (exit_ and entry <= exit_ <= day)


def is_available_alternative(p, listed, day, register_day=False):
    """The one definition of an available alternative, used by the impact levels, the medicine page and the history of newly critical groups.

    A register package `p` of the same substitution group is an available alternative on `day` when
    1. neither its VNR nor an old VNR is in `listed`, the shortage file of that day, and
    2. it is on the market that day: its market entry and exit dates say so (`on_market`), and
    3. on the register's own day, the register's flags agree: market flag `Kaupan` is 1 and shortage flag `Saatavuushairio` is 0.

    The register describes only today and has no past flags, so 3 is the only difference between the current view
    (`register_day` true: the impact levels, the medicine page, and the capture of the history dated the same day as the register's `Ajopvm`)
    and every other capture of the history (`register_day` false). It is written here once. In the other captures `on_market` reads the market dates;
    a package with no entry date has no dates to read, so today's market flag decides for it. On 23 Nov 2026 nine register packages have an entry date and no exit date
    while the flag says they are not on the market; the flag wins on the register's day. An empty shortage flag is not "0", so it does not count.
    """
    if ({p['vnr']} | p['old']) & listed or not on_market(p, day):
        return False
    return not register_day or (p['market'] == '1' and p.get('shortage_flag', '0') == '0')


def group_states(day, rows, members, alias, register_day=False):
    """{group: True when no member is an available alternative} for every group with a package listed in this capture.
    `register_day` is true only for a capture dated the same day as the register; see is_available_alternative."""
    listed = {r['NordicArticleNumber'] for r in rows}
    groups = {alias[v] for v in listed if v in alias}
    return {g: not any(is_available_alternative(p, listed, day, register_day) for p in members[g]) for g in groups}


def newly_critical(snapshots, members, register_date=None):
    """Events when a substitution group lost its last available alternative.

    `members` maps a group code to its register packages ({'vnr', 'old', 'market', 'entry', 'exit', ...}).
    A group is critical in a capture when a package in it is listed and no other package is an available alternative (is_available_alternative).
    The first capture, and the first after a gap of more than MAX_GAP_DAYS, only sets the starting state. After that a
    group changes state only when the new state holds in CONFIRM_CAPTURES consecutive captures, each at most
    MAX_GAP_DAYS apart. A change to critical is an event, dated by the first capture of the new state and the capture before it.
    """
    alias = {}
    for g, packs in members.items():
        for p in packs:
            for v in {p['vnr']} | p['old']:
                alias.setdefault(v, g)
    days = [d for d, _ in snapshots]
    raw = [group_states(d, rows, members, alias, d == register_date) for d, rows in snapshots]
    listed = [{r['NordicArticleNumber'] for r in rows} for _, rows in snapshots]
    stable, out = None, []
    for i, day in enumerate(days):
        if stable is None or is_gap(days[i - 1], day):
            stable = dict(raw[i])
            continue
        window = range(i, i + CONFIRM_CAPTURES)
        if window[-1] >= len(days) or any(is_gap(days[j], days[j + 1]) for j in window[:-1]):
            continue
        for g in sorted(set(raw[i]) | {g for g, v in stable.items() if v}):
            now = raw[i].get(g, False)
            if stable.get(g, False) == now or any(raw[j].get(g, False) != now for j in window):
                continue
            stable[g] = now
            if now:
                out.append({'group': g, 'date': day, 'after': days[i - 1], 'vnrs': sorted(v for v in listed[i] if alias.get(v) == g)})
    return out
