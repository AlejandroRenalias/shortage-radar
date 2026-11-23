"""Index of packages that were on the list earlier and are not now, for the search on the shortage list.

`removed.json` is loaded only when a search finds nothing on the current list, so the first page stays light.
One row for each VNR that is not listed now: its most recently seen notice, with the captures that show it
(`last_seen`) and the stretches between captures that were not observed (`gaps`, scripts/gaps.py).
A row says only what the captures show; leaving the list does not show that supply returned.
"""
FIELDS = ('NordicArticleNumber', 'name', 'strength', 'form', 'pack_label', 'substances', 'atc', 'Company', 'first_seen', 'last_seen', 'removed_on', 'removed_after_gap', 'gaps')


def removed_index(events):
    """Rows for VNRs with no current notice, most recently seen first."""
    listed = {e['NordicArticleNumber'] for e in events if not e['removed_on']}
    latest = {}
    for e in events:
        vnr = e['NordicArticleNumber']
        if e['removed_on'] and vnr not in listed and (vnr not in latest or (e['last_seen'], e['removed_on']) > (latest[vnr]['last_seen'], latest[vnr]['removed_on'])):
            latest[vnr] = e
    rows = [{k: e[k] for k in FIELDS if e.get(k) not in (None, '', [])} for e in latest.values()]
    return sorted(rows, key=lambda r: (r['last_seen'], r['NordicArticleNumber']), reverse=True)
