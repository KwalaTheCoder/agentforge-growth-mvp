"""Deterministic, read-only research prioritization; never predicts buying intent."""
from datetime import date
from urllib.parse import urlparse
from growth_operations import _date

TERMINAL={'Won','Lost'}

def _valid_url(value):
    try:
        u=urlparse(str(value or '').strip())
        return u.scheme in ('https','http') and bool(u.hostname)
    except ValueError:
        return False

def prioritize(record, today=None):
    today=today or date.today()
    r=dict(record)
    stage=str(r.get('stage') or 'Research').strip()
    if stage in TERMINAL:
        return {'company':str(r.get('company') or ''),'stage':stage,'research_score':0,
                'next_action':'No action: closed record','reasons':['Terminal pipeline stage'],
                'outreach_ready':False,'outreach_reason':'Closed record','followup_due':False,
                'source_url':str(r.get('source_url') or '')}
    score=0; reasons=[]
    if str(r.get('company') or '').strip() and _valid_url(r.get('source_url')):
        score+=10; reasons.append('Company and public source recorded (+10)')
    if str(r.get('service') or '').strip():
        score+=10; reasons.append('Service fit recorded (+10; not verified)')
    if bool(r.get('identity_checked')):
        score+=15; reasons.append('Identity manually checked (+15)')
    evidence=bool(str(r.get('need_evidence') or '').strip() and _valid_url(r.get('evidence_url')))
    if evidence:
        score+=20; reasons.append('Need description and evidence URL recorded (+20; not independent proof)')
    if evidence and bool(r.get('need_checked')):
        score+=15; reasons.append('Need evidence manually reviewed (+15)')
    if str(r.get('contact_channel') or '').strip() and bool(r.get('contact_permission_checked')):
        score+=10; reasons.append('Permitted contact route manually recorded (+10)')
    followup=str(r.get('followup') or '').strip(); due=_date(followup)
    due_now=bool(due and due<=today)
    if due_now:
        score+=20; reasons.append('Follow-up due or overdue (+20; scheduling priority only)')
    elif followup and due is None:
        reasons.append('Invalid follow-up date; review manually')
    score=min(score,100)
    # Gate is evaluated independently from priority score.
    from lead_qualification import assess_lead
    assessment=assess_lead(r)
    ready=assessment['status']=='Ready for human outreach review'
    if due_now:
        action='Review scheduled follow-up (manual only)'
    elif not str(r.get('company') or '').strip() or not _valid_url(r.get('source_url')):
        action='Confirm company and source'
    elif not bool(r.get('identity_checked')):
        action='Verify company identity'
    elif not evidence:
        action='Research documented business need (do not infer from GitHub issues)'
    elif not bool(r.get('need_checked')):
        action='Manually review evidence'
    elif not ready:
        action='Verify service fit and permitted business contact route'
    elif stage=='Draft ready':
        action='Human-review saved draft and factual claims'
    else:
        action='Consider drafting a proposal for human review'
    return {'company':str(r.get('company') or ''),'stage':stage,'research_score':score,
            'next_action':action,'reasons':reasons,'outreach_ready':ready,
            'outreach_reason':('All qualification checks recorded; human approval still required' if ready
                               else 'Qualification incomplete; outreach not authorized'),
            'followup_due':due_now,'source_url':str(r.get('source_url') or '')}

def ranked(records,today=None):
    result=[prioritize(r,today) for r in records]
    return sorted(result,key=lambda x:(not x['followup_due'],x['stage'] in TERMINAL,
                                       -x['research_score'],x['company'].casefold()))
