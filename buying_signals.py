"""Conservative public GitHub issue signal research. No contact harvesting or sending."""
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import requests

API = 'https://api.github.com'
HEADERS = {'Accept':'application/vnd.github+json', 'User-Agent':'AgentForge-Research/1.6'}
PAID = re.compile(r'\b(?:paid bounty|paid contract|hiring (?:a |an )?(?:freelancer|contractor)|seeking (?:a |an )?(?:freelancer|contractor)|looking for (?:a |an )?(?:freelancer|contractor)|budget (?:of|is|for)|contractor needed|paid freelance)\b|(?:[$€£]\s*\d[\d,]*(?:\.\d+)?)', re.I)
TECH = re.compile(r'\b(?:bug|broken|error|failure|fails|performance|scalability|integration|migration|security|automation|api|deployment|outage|slow|feature request|help wanted)\b', re.I)
NEGATIVE = re.compile(r'\b(?:unpaid|volunteer only|no budget|not hiring|no payment|bounty closed|already assigned|spam)\b', re.I)
SERVICES = {'AI / Automation':r'\b(?:llm|ai agent|chatbot|automation|rag|machine learning)\b',
            'Python / Backend':r'\b(?:python|fastapi|django|backend|api|database|postgres)\b',
            'Full-stack / Web':r'\b(?:react|next\.?js|vue|frontend|website|web app|typescript)\b',
            'DevOps / Cloud':r'\b(?:docker|kubernetes|terraform|deployment|ci/cd|cloud|aws)\b',
            'Cybersecurity':r'\b(?:security|vulnerability|hardening|pentest|cve)\b',
            'Data / Scraping':r'\b(?:data pipeline|etl|scraping|data extraction|analytics)\b'}

def classify_issue(issue):
    title=str(issue.get('title') or '')[:300]
    body=str(issue.get('body') or '')[:3500]
    text=title+'\n'+body
    labels=[str(x.get('name') or '') for x in (issue.get('labels') or []) if isinstance(x,dict)]
    combined=text+'\n'+' '.join(labels)
    services=[name for name,pattern in SERVICES.items() if re.search(pattern,combined,re.I)]
    paid=PAID.search(text)
    negative=NEGATIVE.search(text)
    tech=TECH.search(combined)
    if paid and not negative:
        kind='Explicit payment/contract wording — unverified'
        score=75 if services else 60
        evidence=paid.group(0)
    elif tech:
        kind='Public technical need — not a buying signal'
        score=35 if services else 20
        evidence=tech.group(0)
    else:
        kind='No relevant buying signal detected'
        score=5
        evidence='No specific payment or technical-need phrase detected'
    if negative:
        score=min(score,10)
        kind='Negative/closed payment signal'
        evidence=negative.group(0)
    return {'title':title,'url':str(issue.get('html_url') or ''),'kind':kind,
            'score':score,'evidence_phrase':evidence,'services':', '.join(services) or 'Not established',
            'state':str(issue.get('state') or ''), 'updated_at':str(issue.get('updated_at') or ''),
            'excerpt':re.sub(r'\s+',' ',body)[:320],
            'buyer_verified':False, 'contact_permission_verified':False}

def research_issues(org_url, max_repos=4, max_issues_per_repo=15, days=90):
    """Review recent open issues from top public repos; no search endpoint or credentials required."""
    parsed=urlparse(str(org_url))
    login=parsed.path.strip('/')
    if parsed.scheme!='https' or parsed.hostname!='github.com' or not re.fullmatch(r'[A-Za-z0-9-]{1,39}',login):
        raise ValueError('Provide an official GitHub organization URL')
    max_repos=max(1,min(int(max_repos),6))
    max_issues_per_repo=max(1,min(int(max_issues_per_repo),30))
    days=max(1,min(int(days),365))
    cutoff=datetime.now(timezone.utc)-timedelta(days=days)
    session=requests.Session();session.headers.update(HEADERS)
    def get(url,params):
        response=session.get(url,params=params,timeout=25)
        if response.status_code in (403,429):
            raise RuntimeError('GitHub rate limit reached. Stop and retry after reset; do not repeatedly refresh.')
        response.raise_for_status()
        return response.json()
    try:
        repos=get(f'{API}/orgs/{login}/repos',{'sort':'pushed','direction':'desc','per_page':max_repos*2})
        if not isinstance(repos,list): raise ValueError('Unexpected repositories response')
        chosen=[r for r in repos if not r.get('fork') and not r.get('archived')][:max_repos]
        findings=[]; checked=[]
        for repo in chosen:
            repo_name=str(repo.get('name') or '')
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',repo_name):continue
            issues=get(f'{API}/repos/{login}/{repo_name}/issues',{'state':'open','sort':'updated','direction':'desc','per_page':max_issues_per_repo})
            if not isinstance(issues,list):continue
            checked.append(repo_name)
            for issue in issues:
                if 'pull_request' in issue:continue
                url=str(issue.get('html_url') or '')
                if not url.startswith(f'https://github.com/{login}/{repo_name}/issues/'):continue
                updated=str(issue.get('updated_at') or '')
                try:
                    if datetime.fromisoformat(updated.replace('Z','+00:00'))<cutoff:continue
                except ValueError:continue
                findings.append(classify_issue(issue))
        findings.sort(key=lambda x:(x['score'],x['updated_at']),reverse=True)
        return {'organization':login,'repos_checked':checked,'issues_checked':len(findings),
                'results':findings[:60], 'limitations':'Recent open issues from a limited sample of public repositories only. Not a complete audit, not evidence of a buyer or permission to contact.'}
    finally:
        session.close()
