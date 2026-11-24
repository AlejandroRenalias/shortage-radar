"""Small data files for single pages, so a page does not download the whole archive.

`p/NN.json` holds every event (current or gone) of the packages whose VNR ends in NN, for the medicine page.
It also holds, for the substitution groups of its current packages, the other packages in each group.
`summary.json` holds the counts and a few packages that the home, trends and about pages need.
"""
from collections import Counter
from datetime import date, timedelta

from triage import counts, with_aliases

META_KEYS = ('archive_start', 'snapshot_date', 'source_metadata', 'generated_at', 'last_checked')
LONGEST = 8
NEWEST = 8
SOON_DAYS = 14  # 'starting within 2 weeks': start date after the data date and up to 14 days after it (day 14 in, day 15 out). site/lib.js SOON_DAYS is the same.


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
    # Every count and every list link on the home page uses the data date (snapshot_date), never the date of the visitor's clock.
    cutoff = (date.fromisoformat(meta['snapshot_date']) + timedelta(days=SOON_DAYS)).isoformat()
    soon = sum(meta['snapshot_date'] < e['UnavailableFrom'] <= cutoff for e in current)
    later = sum(e['UnavailableFrom'] > cutoff for e in current)
    return dict(meta, total=len(current), short_now=len(current) - soon - later, expected_soon=soon, expected_later=later, company_count=len({e['Company'] for e in current}),
                forms=dict(Counter(e.get('form', '') for e in current)),
                atc=dict(Counter((e.get('atc') or '')[:3] for e in current)),
                companies=dict(Counter(e['Company'] for e in current)), impact=with_aliases(counts(current)),
                longest=started[:LONGEST], newest=started[::-1][:NEWEST])
