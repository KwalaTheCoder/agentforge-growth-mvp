"""v5.0: evidence-only research routing. No buyer qualification or outreach."""
from datetime import datetime, timezone


def decide(relevance, *, now=None):
    """Route evidence to Investigate/Monitor/Archive using conservative rules."""
    now = now or datetime.now(timezone.utc)
    rows = []
    for original in relevance.get('items', []):
        row = dict(original)
        score = max(0, min(100, int(row.get('v49_priority') or 0)))
        days = row.get('age_days')
        state = str(row.get('current_state') or '').lower()
        checked = row.get('rechecked') is True
        flags = row.get('evidence_flags') or []
        test = ('Likely test/placeholder issue' in flags or
                'test issue' in str(row.get('title') or '').lower())
        explicit = row.get('payment_wording_found') is True or row.get('external_work_wording_found') is True
        if test or (checked and state == 'closed') or (days is not None and days > 1460 and not explicit):
            decision, reason = 'Archive', 'Test, closed, or very old evidence without explicit work request'
        elif checked and state == 'open' and days is not None and days <= 365 and score >= 50 and explicit:
            decision, reason = 'Investigate', 'Recent open issue with explicit wording; verify original context and funding'
        else:
            decision, reason = 'Monitor', 'Insufficient current, explicit evidence for active investigation'
        row.update(decision=decision, decision_reason=reason,
                   commercial_need_verified=False, contact_permission_verified=False,
                   outreach_authorized=False)
        rows.append(row)
    order = {'Investigate': 0, 'Monitor': 1, 'Archive': 2}
    rows.sort(key=lambda r: (order[r['decision']], -r.get('v49_priority', 0), str(r.get('url') or '')))
    counts = {key: sum(r['decision'] == key for r in rows) for key in order}
    return {'company': relevance.get('company', ''), 'assessed_at_utc': now.isoformat(),
            'counts': counts, 'items': rows, 'investigate': [r for r in rows if r['decision'] == 'Investigate'],
            'monitor': [r for r in rows if r['decision'] == 'Monitor'],
            'archive': [r for r in rows if r['decision'] == 'Archive'],
            'qualification': 'Research Only — manual verification required',
            'commercial_need_verified': False, 'contact_permission_verified': False,
            'outreach_authorized': False, 'crm_modified': False, 'messages_sent': False,
            'scope': 'Evidence triage only; no inferred buyer intent, budget, or contact permission'}
