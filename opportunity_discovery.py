"""Read-only GitHub paid-work candidate discovery. No wallet, contact or CRM writes."""
import re
from urllib.parse import urlparse
import requests
from direct_b2b import API, HEADERS, classify_public_issue, assess_payment_evidence

# Search issue titles/labels first to avoid matching incidental mentions in long comments.
# GitHub may change indexing or ranking; these are discovery heuristics only.
QUERIES = {
    "Bounty": [
        'is:issue is:open bounty in:title',
        'is:issue is:open bounty in:labels',
        'is:issue is:open "reward" in:title',
    ],
    "Paid work": [
        'is:issue is:open "paid" in:title',
        'is:issue is:open "hiring" in:title',
        'is:issue is:open "contract" in:title',
    ],
    "Budget": [
        'is:issue is:open "budget" in:title',
        'is:issue is:open "USD" in:title',
        'is:issue is:open "USDC" in:title',
    ],
}

SKILLS = {
    "AI / Automation": (r'\b(?:llm|ai agent|machine learning|openai|ollama|rag|automation)\b', 4),
    "Python / Backend": (r'\b(?:python|fastapi|django|backend|rest api|webhook|node\.js)\b', 4),
    "Frontend / Full-stack": (r'\b(?:react|next\.js|frontend|full.stack|typescript|vue)\b', 4),
    "DevOps / Cloud": (r'\b(?:devops|docker|kubernetes|terraform|aws|ci/cd|cloud)\b', 4),
    "Cybersecurity": (r'\b(?:security|vulnerabilit|hardening|pentest|authentication)\b', 4),
}

def parse_issue_url(url):
    p = urlparse(str(url or '').strip())
    parts = p.path.strip('/').split('/')
    if p.scheme != 'https' or p.hostname not in ('github.com','www.github.com') or len(parts) != 4 or parts[2] != 'issues' or not parts[3].isdigit():
        raise ValueError('Expected a GitHub issue URL: https://github.com/OWNER/REPO/issues/123')
    for name in parts[:2]:
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', name):
            raise ValueError('Invalid repository path.')
    return parts[0], parts[1], int(parts[3])

from github_reliability import CLIENT, RateLimited
from opportunity_intelligence import analyze_issue

def _request(url, params=None):
    # Cache issue bodies longer than searches; stale issue data is NOT used for payment verification.
    ttl = 900 if '/search/' in url else 3600
    return CLIENT.get(url, params=params, ttl=ttl)

def inspect_issue(url):
    """Fetch the current issue body from GitHub; never follow arbitrary URLs."""
    owner,repo,num=parse_issue_url(url)
    raw=_request(f'{API}/repos/{owner}/{repo}/issues/{num}')
    if raw.get('pull_request'):
        raise ValueError('Pull requests are not treated as open paid issues.')
    return {
        'title':str(raw.get('title') or '')[:300],
        'url':f'https://github.com/{owner}/{repo}/issues/{num}',
        'repository':f'{owner}/{repo}',
        'body':str(raw.get('body') or '')[:50000],
        'excerpt':str(raw.get('body') or '')[:500],
        'state':str(raw.get('state') or ''),
        'updated_at':str(raw.get('updated_at') or ''),
        'labels':', '.join(x.get('name','') for x in raw.get('labels',[]) if isinstance(x,dict))[:250],
    }

def assess_work_availability(issue):
    """Conservative, text-only availability triage; not a contract or payout check."""
    title = str(issue.get('title') or '')[:500]
    body = str(issue.get('body') or issue.get('excerpt') or '')[:50000]
    text = title + "\n" + body
    if issue.get('state') == 'closed':
        return {'work_availability': 'Already Implemented / Claimed',
                'availability_reason': 'Issue is closed; reopening requires manual verification.'}
    # Proposal from the implementer requesting payment for work already delivered.
    delivered = bool(re.search(r'\b(?:implements?|implemented|delivered|completed|merged|shipped|14/14 unit tests passing|changes? delivered)\b', body, re.I))
    existing_pr = bool(re.search(r'(?:\bpull request\s*:\s*#\d+|github\.com/[^\s]+/pull/\d+|\bPR\s*#\d+)', body, re.I))
    payout_request = bool(re.search(r'\b(?:bounty proposal|designated payout rail|payout address|payment address|bounty payout|requesting payout)\b', text, re.I))
    if delivered and existing_pr and payout_request:
        return {'work_availability': 'Already Implemented / Claimed',
                'availability_reason': 'Author describes delivered work, an existing PR, and a payout request.'}
    if re.search(r'\b(?:proposal awaiting (?:maintainer )?approval|pending maintainer approval|bounty proposal)\b', title, re.I):
        return {'work_availability': 'Proposal Awaiting Maintainer Approval',
                'availability_reason': 'Proposal or approval language; no open assignment is established.'}
    if re.search(r'\b(?:already claimed|assigned to|bounty claimed|work completed|task completed)\b', text, re.I):
        return {'work_availability': 'Already Implemented / Claimed',
                'availability_reason': 'Claimed or completed work is mentioned; review context manually.'}
    # Only explicit invitation, not merely 'bounty' or 'help wanted'.
    invitation = re.search(r'\b(?:open for applicants|applications? (?:are )?open|looking for (?:a |an )?(?:[\w-]+ )?(?:developer|contractor|freelancer|contributor)|seeking (?:a |an )?(?:developer|contractor|freelancer)|apply to (?:work|claim)|available to claim|unclaimed bounty)\b', text, re.I)
    if invitation and issue.get('state') == 'open':
        return {'work_availability': 'Open for Applicants',
                'availability_reason': 'Explicit invitation detected; assignment and terms still require manual verification.'}
    return {'work_availability': 'Unknown — Manual Review',
            'availability_reason': 'No reliable explicit evidence that work is open to new applicants.'}

def rank_issue(issue):
    text=(str(issue.get('title') or '')+'\n'+str(issue.get('body') or issue.get('excerpt') or ''))[:50000]
    category=classify_public_issue({**issue,'excerpt':text})
    payment=assess_payment_evidence({**issue,'body':text})
    # Numeric reward plus an explicit bounty offer can be a candidate, never verified.
    if (category['category'] != 'Paid Opportunity Candidate'
            and re.search(r'\bbounty\b', text, re.I)
            and re.search(r'(?:\d+(?:\.\d+)?\s*(?:USDC|USD|EUR)|[$€£]\s*\d+)', text, re.I)):
        category={**category,'category':'Paid Opportunity Candidate'}
    matches=[name for name,(pattern,_) in SKILLS.items() if re.search(pattern,text,re.I)]
    availability=assess_work_availability(issue)
    status=payment['funding_status']
    is_open=issue.get('state') == 'open'
    # Score = research priority, not likelihood of payment.
    score=(35 if category['category']=='Paid Opportunity Candidate' else 0)
    score+=min(25, 8*len(matches))
    score+=10 if is_open else 0
    score-=45 if status=='Unfunded' else 0
    score-=35 if not is_open else 0
    if availability['work_availability'] == 'Already Implemented / Claimed':
        score=0
    elif availability['work_availability'] == 'Proposal Awaiting Maintainer Approval':
        score=max(0,score-30)
    score=max(0,min(70,score))
    intelligence=analyze_issue(issue)
    return {
        **intelligence,
        'title':issue.get('title',''), 'url':issue.get('url',''),
        'repository':issue.get('repository',''),
        'state':issue.get('state','unknown'),
        'classification':category['category'],
        'funding_status':status,
        **availability,
        'skills':', '.join(matches) if matches else 'No skill match detected',
        'priority_score':score,
        'updated_at':issue.get('updated_at',''),
        'commercially_verified':False,
        'manual_review_required':True,
    }

def assess_actionability(row):
    """Conservative evidence-based research queue; not a promise of paid work."""
    if row.get('intelligence_label') == 'Not an Opportunity':
        return 'Excluded', row.get('intelligence_reason','No paid-work evidence')
    if row['work_availability'] == 'Already Implemented / Claimed':
        return 'Excluded', 'Existing contribution, claimed/completed work, or closed issue.'
    if row.get('intelligence_label') == 'Research Candidate':
        return 'Research Only', row.get('intelligence_reason','Manual verification needed')
    if row['funding_status'] == 'Unfunded':
        return 'Research Only', 'Funding explicitly absent.'
    if row['classification'] != 'Paid Opportunity Candidate':
        return 'Research Only', 'No sufficiently explicit paid-work request detected.'
    if row['work_availability'] == 'Open for Applicants':
        return 'Review First', 'Invitation detected, but payment, scope and eligibility remain unverified.'
    return 'Research Only', 'Paid language exists, but applicant availability is not established.'


def discover_opportunities(mode='Bounty', limit=10):
    """Search up to three targeted queries, dedupe, inspect candidates, never write CRM.

    limit caps full-body inspections, not total search hits. Search may be partial.
    """
    if mode not in QUERIES:
        raise ValueError('Unknown search mode')
    limit=max(1,min(20,int(limit)))
    candidates=[]
    seen=set()
    failures=[]
    pending=[]
    incomplete=False
    for query in QUERIES[mode]:
        try:
            payload=_request(f'{API}/search/issues', {
                'q':query,'sort':'updated','order':'desc','per_page':min(50,max(20,limit*2))
            })
        except RateLimited as exc:
            failures.append(f'Search {query}: {exc}')
            break
        except (requests.RequestException,RuntimeError) as exc:
            failures.append(f'Search {query}: {exc}')
            continue
        incomplete |= bool(payload.get('incomplete_results'))
        for result in payload.get('items',[]):
            url=result.get('html_url','')
            if not url or 'pull_request' in result or url in seen:
                continue
            try:
                parse_issue_url(url)
            except ValueError:
                continue
            seen.add(url)
            candidates.append(result)
    # Prioritize obvious offer language in title and labels, not arbitrary body text.
    def preliminary(item):
        title=str(item.get('title') or '')
        labels=' '.join(x.get('name','') for x in item.get('labels',[]) if isinstance(x,dict))
        points=0
        if re.search(r'\b(?:paid bounty|bounty|reward|hiring|paid task)\b',title,re.I): points+=3
        if re.search(r'\b(?:bounty|paid|reward|help wanted)\b',labels,re.I): points+=2
        if re.search(r'(?:[$€£]\s*\d+|\d+\s*(?:USD|USDC|EUR))',title,re.I): points+=2
        if re.search(r'\b(?:proposal|completed|implemented|claimed)\b',title,re.I): points-=3
        return points
    candidates.sort(key=lambda item:(preliminary(item),str(item.get('updated_at') or '')),reverse=True)
    rows=[]
    for index,item in enumerate(candidates[:limit]):
        url=item['html_url']
        try:
            issue=inspect_issue(url)
            row=rank_issue(issue)
            status,reason=assess_actionability(row)
            row['actionability']=status
            row['actionability_reason']=reason
            rows.append(row)
        except RateLimited as exc:
            failures.append(f'{url}: {exc}')
            pending.extend(x['html_url'] for x in candidates[index:limit])
            break
        except (requests.RequestException,ValueError,RuntimeError) as exc:
            failures.append(f'{url}: {exc}')
            pending.append(url)
    priority={'Review First':2,'Research Only':1,'Excluded':0}
    rows.sort(key=lambda r:(priority[r['actionability']],r['priority_score'],r['updated_at']),reverse=True)
    return {'items':rows,'incomplete_results':incomplete,'failures':failures,'mode':mode,
            'unique_search_hits':len(candidates),'inspected_count':len(rows),
            'query_count':len(QUERIES[mode]), 'pending_urls':list(dict.fromkeys(pending)),
            'rate_limit':CLIENT.last_rate, 'blocked_until':CLIENT.blocked_until}


def retry_pending(previous):
    """Retry only pending URLs; preserve prior successful rows and avoid duplicates."""
    pending=list(previous.get('pending_urls') or [])
    rows=list(previous.get('items') or [])
    seen={x.get('url') for x in rows}
    failures=[]
    remaining=[]
    for index,url in enumerate(pending):
        if url in seen: continue
        try:
            issue=inspect_issue(url)
            row=rank_issue(issue)
            status,reason=assess_actionability(row)
            row['actionability']=status
            row['actionability_reason']=reason
            rows.append(row)
            seen.add(url)
        except RateLimited as exc:
            failures.append(f'{url}: {exc}')
            remaining.extend(pending[index:])
            break
        except (requests.RequestException,ValueError,RuntimeError) as exc:
            failures.append(f'{url}: {exc}')
            remaining.append(url)
    priority={'Review First':2,'Research Only':1,'Excluded':0}
    rows.sort(key=lambda r:(priority.get(r['actionability'],0),r['priority_score'],r['updated_at']),reverse=True)
    return {**previous,'items':rows,'inspected_count':len(rows),'pending_urls':remaining,
            'failures':failures,'rate_limit':CLIENT.last_rate,'blocked_until':CLIENT.blocked_until}
