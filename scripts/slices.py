"""Small data files for single pages, so a page does not download the whole archive.

`p/NN.json` holds every event (current or gone) of the packages whose VNR ends in NN, for the medicine page.
It also holds, for the substitution groups of its current packages, the other packages in each group.
`summary.json` holds the counts and a few packages that the home, trends and about pages need.
"""
from collections import Counter

from triage import counts

META_KEYS = ('archive_start', 'snapshot_date', 'source_metadata', 'generated_at', 'last_checked')
LONGEST = 8
NEWEST = 8


def shard_name(vnr):
    return vnr[-2:]


def package_shards(events, meta, groups=None):
    """Return {'00': {...meta, 'events': [...], 'groups': {...}}, ..., '99': ...}; every shard exists so the page never meets a missing file."""
    groups = groups or {}
    shards = {f'{n:02d}': dict(meta, events=[], groups={}) for n in range(100)}
    for e in events:
        shard = shards[shard_name(e['NordicArticleNumber'])]
        shard['events'].append(e)
        g = e.get('substitution_group')
        if not e.get('removed_on') and g in groups:
            shard['groups'][g] = groups[g]
    return shards


def summary(current, meta):
    """Counts by raw form, by ATC prefix (3 letters) and by company, the longest running and the newest current packages."""
    started = sorted((e for e in current if e['UnavailableFrom'] <= meta['snapshot_date']), key=lambda e: e['UnavailableFrom'])
    soon = sum(e['UnavailableFrom'] > meta['snapshot_date'] for e in current)
    return dict(meta, total=len(current), short_now=len(current) - soon, expected_soon=soon, company_count=len({e['Company'] for e in current}),
                forms=dict(Counter(e.get('form', '') for e in current)),
                atc=dict(Counter((e.get('atc') or '')[:3] for e in current)),
                companies=dict(Counter(e['Company'] for e in current)), impact=counts(current),
                longest=started[:LONGEST], newest=started[::-1][:NEWEST])
