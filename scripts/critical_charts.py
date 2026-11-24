"""Small charts and icons for the critical medicines pages: plain inline SVG and HTML, no images, no scripts.

Every chart comes with a table for screen readers (class `sr-only`) that holds the same numbers. Colour never carries meaning alone:
each bar has its label and value, "starts later" is hatched, "start unknown" is dashed, and gaps in the captures are hatched.
Facts only: the charts show counts and dates and suggest no treatment.
"""
from datetime import date
from html import escape

from critical_copy import ATC_GROUPS_FI, ROUTE_NAMES_FI, bi, plain, swap, swap_attr, t

E = lambda value: escape(str(value if value is not None else ''), quote=True)

# ATC level 1 groups (first letter of the code), named as the WHO names them.
ATC_GROUPS = {
    'A': 'Alimentary tract and metabolism', 'B': 'Blood and blood-forming organs', 'C': 'Cardiovascular system', 'D': 'Dermatologicals',
    'G': 'Genito-urinary system and sex hormones', 'H': 'Systemic hormonal preparations', 'J': 'Anti-infectives for systemic use',
    'L': 'Antineoplastic and immunomodulating agents', 'M': 'Musculo-skeletal system', 'N': 'Nervous system', 'P': 'Antiparasitic products',
    'R': 'Respiratory system', 'S': 'Sensory organs', 'V': 'Various',
}
INJECTION = {'into a vein', 'into a muscle', 'under the skin', 'into a joint', 'around a joint', 'into a bursa', 'into the skin', 'epidural'}
ORAL = {'by mouth', 'under the tongue'}
ROUTE_NAMES = {'injection': 'Injection or infusion', 'oral': 'By mouth or under the tongue', 'eye': 'Into the eye', 'other': 'Other or mixed route'}
ICON = {
    'injection': '<path d="M15 4l5 5M13.500 6.500l4 4M10 10l5.500-5.500 4 4L14 14M10 10l-6 6v4h4l6-6M7 17l-3 3M9.500 12.500l2 2"/>',
    'oral': '<rect x="3" y="9" width="18" height="6" rx="3" transform="rotate(-35 12 12)"/><path d="M9.500 8.500l5 7"/>',
    'eye': '<path d="M2 12s3.500-7 10-7 10 7 10 7-3.500 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    'other': '<circle cx="12" cy="12" r="8"/><path d="M8 12h8"/>',
}


def route_group(route):
    if 'eye' in route.split():
        return 'eye'
    if route in INJECTION:
        return 'injection'
    return 'oral' if route in ORAL else 'other'


def route_kind(routes):
    """The one group that all routes of the package belong to; several groups, or none, count as "other or mixed"."""
    groups = {route_group(r) for r in routes or []}
    return groups.pop() if len(groups) == 1 else 'other'


def route_icon(kind, size=18):
    return (f'<svg class="uicon eu-route-icon" viewBox="0 0 24 24" width="{size}" height="{size}" aria-hidden="true" focusable="false">{ICON[kind]}</svg>')


def route_label(routes):
    """Icon and plain label for the route of a package; the full route text stays in the details."""
    kind = route_kind(routes)
    return f'<span class="eu-route-tag">{route_icon(kind, 16)}{bi(E(ROUTE_NAMES[kind]), E(ROUTE_NAMES_FI[kind]))}</span>'


def route_counts(rows, status='ongoing'):
    out = dict.fromkeys(ROUTE_NAMES, 0)
    for r in rows:
        if r['status'] == status and r['match_type'] == 'exact':
            out[route_kind(r.get('product_routes'))] += 1
    return out


def route_row(rows):
    counts = route_counts(rows)
    items = ''.join(f'<li>{route_icon(k, 22)}<span><strong>{n:,}</strong> {bi(E(ROUTE_NAMES[k]).lower(), E(ROUTE_NAMES_FI[k]).lower())}</span></li>' for k, n in counts.items())
    return f'<ul class="eu-routes"{swap_attr("aria-label", "chart.routes.label")}>{items}</ul>'


HATCH = ('<defs><pattern id="eu-hatch-later" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="var(--white)"/>'
         '<path d="M0 0v6" stroke="var(--soon)" stroke-width="3"/></pattern></defs>')


def bar_svg(parts, top):
    """One bar track as SVG (a style attribute is blocked by the page's content security policy). `parts` is [(class, count)] drawn left to right."""
    x, rects = 0.0, []
    for cls, n in parts:
        w = n / top * 100
        if n:
            rects.append(f'<rect x="{x:.2f}%" width="{w:.2f}%" height="14" class="{cls}"/>')
        x += w
    return f'<svg class="eu-bar-svg" width="100%" height="14" aria-hidden="true" focusable="false"><rect width="100%" height="14" rx="7" class="eu-bar-bg"/>{HATCH}{"".join(rects)}</svg>'


def match_bars(ongoing, types, names):
    """Horizontal bars of ongoing shortages by match type; one table for screen readers."""
    top = max([ongoing[t] for t in types] + [1])
    bars = ''.join(
        f'<li class="eu-bar-row"><span class="eu-bar-name">{E(names[t])}</span><span class="eu-bar-track">{bar_svg([(f"eu-bar-{t}", ongoing[t])], top)}</span>'
        f'<span class="eu-bar-value">{ongoing[t]:,}</span></li>' for t in types)
    table = ''.join(f'<tr><th scope="row">{E(names[t])}</th><td>{ongoing[t]:,}</td></tr>' for t in types)
    return (f'<figure class="eu-chart"><figcaption>Ongoing packages checked, by match</figcaption><ul class="eu-bars" aria-hidden="true">{bars}</ul>'
            f'<div class="sr-only"><table><caption>Ongoing packages checked, by match</caption><thead><tr><th scope="col">Match</th><th scope="col">Packages</th></tr></thead><tbody>{table}</tbody></table></div></figure>')


def group_bars(rows):
    """Stacked horizontal bars by ATC group: ongoing solid, starts later hatched."""
    groups = {}
    for r in rows:
        letter = (r.get('atc') or '')[:1]
        if letter in ATC_GROUPS and r['match_type'] == 'exact':
            g = groups.setdefault(letter, {'ongoing': 0, 'upcoming': 0})
            g[r['status']] += 1
    if not groups:
        return ''
    top = max(g['ongoing'] + g['upcoming'] for g in groups.values())
    bars, table = [], []
    for letter in sorted(groups):
        g = groups[letter]
        name = bi(E(ATC_GROUPS[letter]), E(ATC_GROUPS_FI[letter]))
        bars.append(f'<li class="eu-bar-row"><span class="eu-bar-name"><b>{letter}</b> {name}</span>'
                    f'<span class="eu-bar-track">{bar_svg([("eu-bar-ongoing", g["ongoing"]), ("eu-bar-later", g["upcoming"])], top)}</span>'
                    f'<span class="eu-bar-value">{g["ongoing"] + g["upcoming"]:,}</span></li>')
        table.append(f'<tr><th scope="row">{letter} {name}</th><td>{g["ongoing"]:,}</td><td>{g["upcoming"]:,}</td></tr>')
    legend = f'<p class="eu-legend"><span><svg class="eu-key-svg" viewBox="0 0 24 12" width="24" height="12" aria-hidden="true"><rect width="24" height="12" rx="3" class="eu-bar-ongoing"/></svg>{t("chart.ongoing")}</span><span><svg class="eu-key-svg" viewBox="0 0 24 12" width="24" height="12" aria-hidden="true"><rect width="24" height="12" rx="3" class="eu-bar-later"/></svg>{t("chart.later")}</span></p>'
    return (f'<figure class="eu-chart"><figcaption>{t("chart.groups.caption")}</figcaption>{legend}<ul class="eu-bars" aria-hidden="true">{"".join(bars)}</ul>'
            f'<div class="sr-only"><table><caption>{t("chart.groups.table")}</caption><thead><tr><th scope="col">{t("chart.group")}</th><th scope="col">{t("chart.ongoing")}</th><th scope="col">{t("chart.later")}</th></tr></thead>'
            f'<tbody>{"".join(table)}</tbody></table></div></figure>')


def timeline_strip(notices, archive_start, snapshot_date):
    """One bar for each shortage from first to last capture that listed it. Hatched: captures are missing there (unknown time).
    Dashed outline: the start is unknown. Rows are in the same order as the list below the strip."""
    if not notices:
        return ''
    day = date.fromisoformat
    t0 = min(day(archive_start), min(day(n['first_seen']) for n in notices))
    t1 = day(snapshot_date)
    span = max((t1 - t0).days, 1)
    left, right, row, top = 6, 6, 20, 24
    width = 320
    x = lambda iso: left + (day(iso) - t0).days / span * (width - left - right)
    height = top + row * len(notices) + 6
    parts = ['<defs><pattern id="eu-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="var(--white)"/><path d="M0 0v6" stroke="var(--muted)" stroke-width="2"/></pattern></defs>']
    for year in range(t0.year + (t0.month > 1 or t0.day > 1), t1.year + 1):
        xs = x(f'{year}-01-01')
        parts.append(f'<path d="M{xs:.1f} 14V{height}" class="eu-ax"/><text x="{xs + 3:.1f}" y="11" class="eu-ax-text">{year}</text>')
    for i, n in enumerate(notices):
        y = top + i * row
        end = snapshot_date if n['removed_on'] is None else n['last_seen']
        x0, x1 = x(n['first_seen']), max(x(end), x(n['first_seen']) + 3)
        unknown = n['listed_at_first_capture'] or n['start_unknown']
        cls = 'eu-tl-bar eu-tl-unknown' if unknown else 'eu-tl-bar'
        name = ' '.join(p for p in (n['name'], n['strength']) if p)
        state = ('chart.strip.still', {}) if n['removed_on'] is None else ('chart.strip.last', {'date': n['last_seen']})
        label = {i: plain('chart.strip.label', i, name=name, first=n['first_seen'], state=plain(state[0], i, **state[1]),
                          unknown=plain('chart.strip.unknownstart', i) if unknown else '',
                          gaps=''.join(plain('chart.strip.gap', i, a=g['from'], b=g['to']) for g in n['gaps'])) for i in (0, 1)}
        parts.append(f'<rect x="{x0:.1f}" y="{y}" width="{x1 - x0:.1f}" height="12" rx="3" class="{cls}"><title data-en="{E(label[0])}" data-fi="{E(label[1])}">{E(label[0])}</title></rect>')
        for g in n['gaps']:
            gx0, gx1 = x(g['from']), x(g['to'])
            parts.append(f'<rect x="{gx0:.1f}" y="{y}" width="{max(gx1 - gx0, 2):.1f}" height="12" class="eu-tl-gap"><title{swap("chart.strip.gaptitle", a=g["from"], b=g["to"])}>{E(plain("chart.strip.gaptitle", 0, a=g["from"], b=g["to"]))}</title></rect>')
        for u in n['unseen']:
            ux0, ux1 = x(u['from']), x(u['to'])
            parts.append(f'<rect x="{ux0:.1f}" y="{y}" width="{max(ux1 - ux0, 2):.1f}" height="12" class="eu-tl-gap"><title{swap("chart.strip.unseentitle", a=u["from"], b=u["to"])}>{E(plain("chart.strip.unseentitle", 0, a=u["from"], b=u["to"]))}</title></rect>')
    key = (f'<p class="eu-legend"><span><svg class="eu-key-svg" viewBox="0 0 24 10" width="24" height="10" aria-hidden="true"><rect width="24" height="10" rx="3" class="eu-tl-bar"/></svg>{t("chart.strip.listed")}</span>'
           f'<span><svg class="eu-key-svg" viewBox="0 0 24 10" width="24" height="10" aria-hidden="true"><rect x="1" y="1" width="22" height="8" rx="3" class="eu-tl-bar eu-tl-unknown"/></svg>{t("chart.strip.unknown")}</span>'
           f'<span><svg class="eu-key-svg" viewBox="0 0 24 10" width="24" height="10" aria-hidden="true"><rect width="24" height="12" class="eu-tl-gap"/></svg>{t("chart.strip.nocapture")}</span></p>')
    return (f'<figure class="eu-chart eu-strip"><figcaption>{t("chart.strip.caption")}</figcaption>{key}'
            f'<svg viewBox="0 0 {width} {height}" role="img"{swap_attr("aria-label", "chart.strip.aria", n=len(notices))} class="eu-strip-svg" preserveAspectRatio="xMinYMin meet">{"".join(parts)}</svg></figure>')


def hero_art():
    """Calm abstract picture: soft waves and rising bars, our own drawing. It shows nothing real and suggests no treatment."""
    return ('<svg class="eu-hero-art" viewBox="0 0 640 160" aria-hidden="true" focusable="false" preserveAspectRatio="xMidYMid slice">'
            '<rect width="640" height="160" fill="var(--mint)"/>'
            '<path d="M0 110C80 70 160 130 260 96S440 50 520 84 610 100 640 78V160H0Z" fill="var(--icon-fill)"/>'
            '<path d="M0 134C100 104 190 150 290 122S470 90 560 118 620 124 640 110V160H0Z" fill="var(--green)" opacity=".35"/>'
            '<g fill="var(--green-ink)" opacity=".55"><rect x="60" y="64" width="10" height="40" rx="5"/><rect x="82" y="46" width="10" height="58" rx="5"/><rect x="104" y="76" width="10" height="28" rx="5"/>'
            '<rect x="460" y="40" width="10" height="64" rx="5"/><rect x="482" y="58" width="10" height="46" rx="5"/><rect x="504" y="30" width="10" height="74" rx="5"/></g>'
            '<circle cx="330" cy="46" r="26" fill="var(--white)" opacity=".7"/></svg>')
