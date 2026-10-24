"""Read-only, deterministic growth operations metrics for existing B2B CRM."""
from collections import Counter
from datetime import date

PIPELINE = ('Research','Qualified','Draft ready','Contacted','Replied','Negotiating','Won','Lost')

def _date(value):
    try:
        return date.fromisoformat(str(value).strip()[:10]) if value else None
    except ValueError:
        return None

def summarize(records, today=None):
    today = today or date.today()
    records = list(records)
    stages = Counter(str(r.get('stage') or 'Research') for r in records)
    due, overdue, ready, research, invalid_dates = [], [], [], [], []
    for r in records:
        stage = str(r.get('stage') or 'Research')
        followup = str(r.get('followup') or '').strip()
        due_date = _date(followup)
        # Won/Lost are terminal; never imply they need follow-up.
        if followup and due_date is None:
            invalid_dates.append(r)
        if due_date and stage not in ('Won','Lost') and due_date <= today:
            due.append(r)
            if due_date < today:
                overdue.append(r)
        if stage == 'Draft ready' and str(r.get('draft') or '').strip():
            ready.append(r)
        if stage == 'Research':
            research.append(r)
    return {
        'total':len(records), 'stages':{s:stages.get(s,0) for s in PIPELINE},
        'other_stages':{k:v for k,v in stages.items() if k not in PIPELINE},
        'due':due,'overdue':overdue,'drafts_for_review':ready,
        'research':research,'invalid_dates':invalid_dates,
        'qualified_or_later':sum(v for k,v in stages.items() if k in PIPELINE[1:6]),
    }

def rows(records):
    """Whitelist fields for display; do not expose contact notes or draft text."""
    return [dict(company=str(r.get('company') or ''),
                 stage=str(r.get('stage') or ''),
                 followup=str(r.get('followup') or ''),
                 service=str(r.get('service') or ''),
                 source_url=str(r.get('source_url') or '')) for r in records]
