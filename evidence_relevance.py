"""v4.9: Conservative evidence relevance triage; never verifies buying intent."""
import re
from datetime import datetime, timezone

TEST_WORDS = re.compile(r"\b(?:test issue|testing issue|dummy issue|placeholder|test ticket)\b", re.I)
PAYMENT_WORDS = re.compile(r"\b(?:paid bounty|cash bounty|payment offered|offering payment|paid contract available|we will pay|we can pay)\b|\bbounty\s*[:=]\s*[$€£]\s*\d+|\bbudget\s*(?:is|of)\s*[$€£]\s*\d+", re.I)
REQUEST_WORDS = re.compile(r"\b(?:looking for (?:external |outside )?(?:contractors|developers|contributors)|seeking (?:contractors|developers)|request for proposals|rfp|help wanted|contributors wanted)\b", re.I)

def prioritize(quality, full_report=None, *, min_priority=40):
    """Pure function: no network, no CRM writes; retain rejected rows for audit."""
    full_report = full_report or {}
    gh = full_report.get('github') or {}
    excerpts = {i.get('url'): i for i in gh.get('issues', []) if isinstance(i, dict)}
    output = []
    for item in quality.get('issues', []):
        row = dict(item)
        source = excerpts.get(row.get('url'), {})
        text = ' '.join((str(row.get('title') or ''), str(source.get('excerpt') or '')))
        days = row.get('age_days')
        state = str(row.get('current_state') or '').lower()
        verified_state = bool(row.get('rechecked'))
        test = bool(TEST_WORDS.search(str(row.get('title') or '')))
        paid = bool(PAYMENT_WORDS.search(text))
        request = bool(REQUEST_WORDS.search(text))
        reasons = []
        if test: reasons.append('Likely test/placeholder issue')
        if not verified_state: reasons.append('Current state not verified')
        elif state != 'open': reasons.append('Not currently open')
        if days is None: reasons.append('Missing update date')
        elif days > 730: reasons.append('Last updated over 2 years ago')
        if paid: reasons.append('Payment-related wording: manual validation required')
        if request: reasons.append('External-work/contribution wording: manual validation required')
        if not paid and not request: reasons.append('No explicit external-work request detected in sampled text')
        base = max(0, min(75, int(row.get('research_priority') or 0)))
        score = base + (15 if paid else 0) + (8 if request else 0)
        if days is not None and days > 730: score = min(score, 15)
        if test: score = 0
        if not verified_state or state != 'open': score = min(score, 10)
        if days is None: score = min(score, 10)
        score = min(100, score)
        row.update(v49_priority=score, evidence_flags=reasons,
                   payment_wording_found=paid, external_work_wording_found=request,
                   commercial_need_verified=False, contact_permission_verified=False,
                   recommendation=('Review original source manually' if score >= min_priority else 'Deprioritize; seek newer, stronger evidence'))
        output.append(row)
    output.sort(key=lambda x: (-x['v49_priority'], str(x.get('url') or '')))
    return {'company': quality.get('company',''), 'items': output,
            'review_first': [x for x in output if x['v49_priority'] >= min_priority],
            'deprioritized_count': sum(x['v49_priority'] < min_priority for x in output),
            'minimum_priority': min_priority,
            'qualification': 'Research Only — manual verification required',
            'commercial_need_verified': False, 'contact_permission_verified': False,
            'crm_modified': False, 'messages_sent': False,
            'score_meaning': 'Research evidence triage only; NOT buyer probability, funding verification or outreach permission'}
