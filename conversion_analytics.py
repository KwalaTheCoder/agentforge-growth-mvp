"""Snapshot-only CRM funnel reporting; never infer historical conversions."""
from collections import Counter

STAGES = ('Research', 'Qualified', 'Draft ready', 'Contacted', 'Replied', 'Negotiating', 'Won', 'Lost')
ACTIVE = ('Research', 'Qualified', 'Draft ready', 'Contacted', 'Replied', 'Negotiating')


def snapshot(records):
    """Deduplicate by source URL and report current stage distribution only.

    No history exists in this CRM; stage-to-stage conversion rates are not measurable.
    """
    by_source = {}
    missing_source = []
    for row in records:
        item = dict(row)
        source = str(item.get('source_url') or '').strip()
        if not source:
            missing_source.append(item)
            continue
        prev = by_source.get(source)
        if prev is None or str(item.get('updated_at') or '') > str(prev.get('updated_at') or ''):
            by_source[source] = item
    counts = Counter(str(row.get('stage') or 'Research') for row in by_source.values())
    known = {s: counts.get(s, 0) for s in STAGES}
    other = {k: v for k, v in counts.items() if k not in STAGES}
    total = len(by_source)
    terminal = known['Won'] + known['Lost']
    # Won/closed is a current-state share, NOT a historical conversion rate.
    won_share = (100 * known['Won'] / total) if total else None
    return {
        'total': total, 'stages': known, 'unknown_stages': other,
        'active': sum(known[s] for s in ACTIVE),
        'terminal': terminal, 'won': known['Won'], 'lost': known['Lost'],
        'current_won_share_pct': won_share,
        'missing_source_count': len(missing_source),
        'duplicate_rows_removed': max(0, len(records) - len(missing_source) - total),
        'history_available': False,
        'historical_conversion_rates': None,
        'note': 'Current CRM stage distribution only; no stage-change history or cohort conversion rates.'
    }


def safe_rows(records):
    """Only non-sensitive, display-safe fields; no emails, notes, or draft text."""
    return [dict(company=str(r.get('company') or ''),
                 stage=str(r.get('stage') or 'Research'),
                 service=str(r.get('service') or ''),
                 source_url=str(r.get('source_url') or '')) for r in records]
