"""The one rule for gaps between captures, shared by every part of the build.

Captures are days or weeks apart. When two consecutive captures are more than MAX_GAP_DAYS apart, nothing is known about the
days between them: a notice listed on both sides was not observed in between, and a notice listed only on one side started or
ended at an unknown time in the gap. A gap of exactly MAX_GAP_DAYS days is still short: the captures are joined.
"""
from datetime import date

MAX_GAP_DAYS = 14


def days_between(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def is_gap(a, b):
    """Are two captures (ISO dates, `a` earlier) far enough apart that the days between them are unknown?"""
    return days_between(a, b) > MAX_GAP_DAYS


def add_capture(spans, previous_day, day):
    """Record that a notice was listed in the capture of `day`; `previous_day` is the capture just before it (None for the first).

    `spans` is a list of {'first_seen', 'last_seen'}: runs of captures with no long gap between them. A long gap starts a new span.
    """
    if spans and previous_day is not None and not is_gap(previous_day, day):
        spans[-1]['last_seen'] = day
    else:
        spans.append({'first_seen': day, 'last_seen': day})


def gaps_of(spans):
    """[{'from', 'to', 'days'}] for the stretches between spans: from the last capture of one span to the first of the next."""
    return [{'from': a['last_seen'], 'to': b['first_seen'], 'days': days_between(a['last_seen'], b['first_seen'])} for a, b in zip(spans, spans[1:])]
