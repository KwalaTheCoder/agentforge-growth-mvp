"""Read-only public organization discovery for manual B2B research.

Public GitHub activity is not proof of purchasing intent or contact permission.
"""
import re
from direct_b2b import API
from github_reliability import CLIENT

SERVICE_TERMS = {
    'AI / Automation': ('llm', 'rag', 'ai agent', 'machine learning', 'automation'),
    'Backend / API': ('api', 'backend', 'fastapi', 'django', 'webhook'),
    'Frontend': ('frontend', 'react', 'next.js', 'vue', 'web app'),
    'DevOps': ('deployment', 'ci/cd', 'kubernetes', 'docker', 'terraform'),
    'Security': ('security', 'hardening', 'authentication', 'vulnerability'),
}
def validate_login(login):
    login=str(login or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?',login):
        raise ValueError('Invalid organization login')
    return login

def search_organizations(location, keyword='', limit=10):
    location=str(location or '').strip()
    keyword=str(keyword or '').strip()
    if not location or len(location)>80 or len(keyword)>60 or any(c in location+keyword for c in '\r\n"'):
        raise ValueError('Enter a location (max 80 characters) and optional keyword (max 60).')
    limit=max(1,min(int(limit),20))
    q=f'type:org location:"{location}"'
    if keyword:
        q+=' '+keyword
    payload=CLIENT.get(f'{API}/search/users',params={'q':q,'per_page':limit},ttl=900)
    return [{'login':x['login'],'url':x.get('html_url','')}
            for x in payload.get('items',[]) if x.get('type')=='Organization'
            and re.fullmatch(r'[A-Za-z0-9-]+',x.get('login',''))][:limit]

def organization_research(login, issue_limit=6):
    login=validate_login(login)
    issue_limit=max(1,min(int(issue_limit),10))
    profile=CLIENT.get(f'{API}/orgs/{login}',ttl=3600)
    if profile.get('type')!='Organization':
        raise ValueError('GitHub profile is not an organization.')
    # Search public issues authored in the organization. This is a technical signal,
    # not a purchase request, and the author might be an external contributor.
    issues=CLIENT.get(f'{API}/search/issues',params={
        'q':f'org:{login} is:issue is:open',
        'sort':'updated','order':'desc','per_page':issue_limit
    },ttl=900)
    signals=[]
    for x in issues.get('items',[])[:issue_limit]:
        if x.get('pull_request'):
            continue
        title=str(x.get('title') or '')[:250]
        body=str(x.get('body') or '')[:2000]
        text=(title+' '+body).lower()
        matches=[name for name,words in SERVICE_TERMS.items()
                 if any(re.search(r'(?<![a-z0-9])'+re.escape(w)+r'(?![a-z0-9])',text) for w in words)]
        signals.append({'title':title,'url':x.get('html_url',''),
                        'service_topics':', '.join(matches) or 'Uncategorized',
                        'updated_at':x.get('updated_at',''),
                        'buyer_need_verified':False})
    return {'login':login,'name':str(profile.get('name') or login)[:150],
            'profile_url':f'https://github.com/{login}',
            'description':str(profile.get('description') or '')[:1000],
            'website_unverified':str(profile.get('blog') or '')[:300],
            'location':str(profile.get('location') or '')[:150],
            'signals':signals,'incomplete_results':bool(issues.get('incomplete_results')),
            'buyer_need_verified':False,'contact_permission_verified':False,
            'qualification':'Research Only'}

def research_to_crm_prefill(research):
    """A draft for a human to copy; never persists or auto-qualifies."""
    return {
        'company':research.get('name',''),
        'source_url':research.get('profile_url',''),
        'description':research.get('description',''),
        'country':research.get('location',''),
        'stage':'Research',
        'need_evidence':'',
        'evidence_url':'',
        'contact_channel':'',
        'identity_checked':False,
        'need_checked':False,
        'contact_permission_checked':False,
    }
