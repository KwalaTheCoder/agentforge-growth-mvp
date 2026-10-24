"""v5.1: rank *technical research* candidates, never infer commercial intent."""
from datetime import datetime, timezone
import re

IMPACT_PATTERNS = {
    'incorrect results/data integrity': r'\b(corrupt|incorrect|wrong|nan|data loss|drops? a|missing|no gradients|false positive)\b',
    'runtime failure': r'\b(crash|fails?|failure|broken|exception|error|cannot|does not support|silently overridden)\b',
    'performance/scaling': r'\b(performance|slow|latency|memory leak|multi.gpu|parallelism|scalability)\b',
}

def prioritize(report, *, now=None):
    """Transparent deterministic heuristic. Text matches are hypotheses, not verified impact."""
    now = now or datetime.now(timezone.utc)
    items=[]
    for source in report.get('items', []):
        row=dict(source)
        title=str(row.get('title') or '')
        age=row.get('age_days')
        try: age=int(age) if age is not None else None
        except (ValueError, TypeError): age=None
        state=str(row.get('current_state') or '').lower()
        checked=row.get('rechecked') is True
        flags=row.get('evidence_flags') or []
        placeholder=('Likely test/placeholder issue' in flags or bool(re.search(r'\b(test issue|placeholder|dummy)\b', title, re.I)))
        if age is None or age < 0: freshness=0
        elif age <= 7: freshness=45
        elif age <= 30: freshness=38
        elif age <= 90: freshness=28
        elif age <= 180: freshness=16
        elif age <= 365: freshness=8
        else: freshness=0
        matches=[name for name, pattern in IMPACT_PATTERNS.items() if re.search(pattern,title,re.I)]
        impact=min(30,15*len(matches))
        specificity=10 if len(title.split()) >= 7 else 0
        verification=15 if checked and state=='open' else 0
        score=min(100,freshness+impact+specificity+verification)
        if not checked or state!='open': score=min(score,20)
        if placeholder: score=0
        if age is None: score=min(score,20)
        if age is not None and age>730: score=min(score,15)
        if score >= 75: tier='Deep research'
        elif score >= 40: tier='Quick review'
        else: tier='Low priority'
        row.update(technical_research_score=score,technical_research_tier=tier,
                   potential_impact_keywords=matches,
                   technical_score_explanation=f'freshness={freshness}, title impact hints={impact}, specificity={specificity}, verified open={verification}; conservative caps may apply',
                   commercial_need_verified=False,contact_permission_verified=False,outreach_authorized=False)
        items.append(row)
    items.sort(key=lambda r:(-r['technical_research_score'],str(r.get('url') or '')))
    return {'company':report.get('company',''),'assessed_at_utc':now.isoformat(),
            'items':items,'deep_research':[r for r in items if r['technical_research_tier']=='Deep research'],
            'quick_review':[r for r in items if r['technical_research_tier']=='Quick review'],
            'low_priority':[r for r in items if r['technical_research_tier']=='Low priority'],
            'qualification':'Research Only — manual verification required',
            'commercial_need_verified':False,'contact_permission_verified':False,
            'outreach_authorized':False,'crm_modified':False,'messages_sent':False,
            'scope':'Heuristic ranking of technical research only. No buyer, budget, severity, or outreach claims.'}
