"""AgentForge v1.8: cautious, evidence-based GitHub opportunity screening.

Public issue content is untrusted. No claim of an actual buyer or payment is made.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from opportunity_discovery import HEADERS, TECH, search_public_issues

MONEY = re.compile(r'(?<![\w])(?:(?P<symbol>[$€£])\s?(?P<amount>\d+(?:,\d{3})*(?:\.\d{1,2})?)|(?P<amount2>\d+(?:,\d{3})*(?:\.\d{1,2})?)\s?(?P<currency>USD|EUR|GBP|USDT|USDC))', re.I)
# Avoid matching a price in an unrelated link by limiting evidence to title/body.
PAID = re.compile(r'\b(bounty|paid|payment|reward|compensation|budget|contractor|freelancer|freelance|commission|hire|hiring)\b', re.I)
EXPLICIT = re.compile(r'\b(looking for|seeking|need to hire|hiring|pay(?:ing)?|offering|bounty|reward|paid task|contractor wanted)\b', re.I)
NEGATIVE = re.compile(r'\b(unpaid|no bounty|no budget|not paid|not hiring|no payment|bounty cancelled|bounty canceled|reward withdrawn|already claimed|bounty expired|bounty closed)\b', re.I)
HISTORICAL = re.compile(r'\b(previous bounty|was paid|formerly paid|bounty history|not a bounty|bounty program ended)\b', re.I)


def amounts(text):
    out=[]
    for m in MONEY.finditer(text or ''):
        raw=m.group(0).strip()
        if raw not in out: out.append(raw)
    return out[:5]


def _service_matches(text):
    return [service for service,terms in TECH.items() if any(re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',text,re.I) for term in terms)]


def assess(item):
    """Return conservative screening labels. Score is not purchase probability."""
    title=str(item.get('title') or '')
    body=str(item.get('body') or '')[:12000]
    content=title+'\n'+body
    price=amounts(content)
    keywords=sorted(set(m.group(0).lower() for m in PAID.finditer(content)))[:12]
    neg=bool(NEGATIVE.search(content))
    historic=bool(HISTORICAL.search(content))
    explicit=bool(EXPLICIT.search(content))
    state=str(item.get('state') or '').lower()
    state_reason=str(item.get('state_reason') or '').lower()
    closed=state == 'closed' or state_reason in ('completed','not_planned')
    is_pr=bool(item.get('pull_request'))
    services=_service_matches(content)
    fit=min(100,20+20*len(services)) if services else 10
    if closed or is_pr or neg or historic:
        status='Excluded / needs manual review'
        evidence_score=0
        reasons=[x for x,condition in [('Closed issue',closed),('Pull request, not issue',is_pr),('Explicit non-payment/cancellation',neg),('Historical or negated bounty mention',historic)] if condition]
    elif price and (explicit or keywords):
        status='Payment indication — verify terms'
        evidence_score=75
        reasons=['Currency amount and payment-related language present; no verification of payer, eligibility or payout']
    elif price:
        status='Amount mentioned — context unverified'
        evidence_score=45
        reasons=['Currency amount present; may not be compensation']
    elif explicit and keywords:
        status='Possible paid opportunity — no amount'
        evidence_score=50
        reasons=['Payment or contracting language found; no amount verified']
    elif keywords:
        status='Payment keyword only — weak evidence'
        evidence_score=25
        reasons=['Generic payment keyword found without offer details']
    else:
        status='No payment evidence'
        evidence_score=0
        reasons=['No payment evidence in title or inspected body']
    return {'title':title[:300], 'url':str(item.get('html_url') or ''),
            'repository':str(item.get('repository_url') or '').split('/repos/')[-1],
            'payment_indication':status, 'payment_evidence_score':evidence_score,
            'technical_fit_score':fit, 'amounts':', '.join(price),
            'services':', '.join(services) if services else 'Unspecified',
            'evidence_terms':', '.join(keywords), 'reasons':'; '.join(reasons),
            'issue_state':state or 'unknown', 'updated_at':str(item.get('updated_at') or ''),
            'excerpt':body[:1400], 'verified_buyer':False, 'verified_payment':False,
            'eligible_to_contact':False}


def _issue_api_url(url):
    p=urlparse(str(url))
    if p.scheme != 'https' or p.hostname != 'github.com':
        raise ValueError('Only GitHub public issue URLs are supported')
    parts=[x for x in p.path.split('/') if x]
    if len(parts)!=4 or parts[2]!='issues' or not parts[3].isdigit():
        raise ValueError('Expected GitHub issue URL')
    if not all(re.fullmatch(r'[A-Za-z0-9_.-]+',x) for x in parts):
        raise ValueError('Invalid GitHub repository path')
    return f'https://api.github.com/repos/{parts[0]}/{parts[1]}/issues/{parts[3]}'


def fetch_issue(url):
    endpoint=_issue_api_url(url)
    response=requests.get(endpoint,headers=HEADERS,timeout=18)
    if response.status_code in (403,429):
        raise RuntimeError('GitHub API rate limit or access restriction. Try later.')
    response.raise_for_status()
    data=response.json()
    if data.get('pull_request'):
        raise ValueError('This URL points to a pull request')
    return data


def screen_results(query, limit=15, fetch_details=True):
    candidates,incomplete=search_public_issues(query,limit)
    results=[]; seen=set(); errors=[]
    for candidate in candidates:
        url=candidate.get('url','')
        try:
            endpoint=_issue_api_url(url)
        except ValueError:
            continue
        if endpoint in seen: continue
        seen.add(endpoint)
        if fetch_details:
            try:
                issue=fetch_issue(url)
            except (requests.RequestException,ValueError,RuntimeError) as exc:
                errors.append(f'{url}: {exc}')
                continue
        else:
            # The v1.7 search result lacks full body/state, so do not claim verification.
            issue={'title':candidate.get('title',''), 'body':candidate.get('excerpt',''),
                   'html_url':url, 'repository_url':'https://api.github.com/repos/'+candidate.get('repository',''),
                   'state':'unknown', 'updated_at':candidate.get('updated_at','')}
        results.append(assess(issue))
    results.sort(key=lambda r:(r['payment_evidence_score'],r['technical_fit_score']),reverse=True)
    return results,incomplete,errors


def recent_enough(updated_at, days=90):
    try:
        dt=datetime.fromisoformat(updated_at.replace('Z','+00:00'))
        return (datetime.now(timezone.utc)-dt).days <= days
    except (ValueError,TypeError,AttributeError):
        return False
