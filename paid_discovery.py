"""Conservative discovery of public GitHub issues with explicit monetary signals.
These are research candidates, not verified paid freelance contracts.
"""
from datetime import datetime, timedelta, timezone
import re
import requests

QUERIES = {
    'Paid bounty': 'is:issue is:open bounty in:title,body',
    'Funded work': 'is:issue is:open "paid" "issue" in:body',
    'Contractor requests': 'is:issue is:open "contractor" in:title,body',
}
MONEY = re.compile(r'(?<!\w)(?:USD|EUR|GBP)\s*\d[\d,]*(?:\.\d+)?\b|[$€£]\s*\d[\d,]*(?:\.\d+)?\b|\b(?:paid bounty|bounty of|budget of|reward of|payment of)\b', re.I)
NEGATIVE = re.compile(r'\b(?:unpaid|no bounty|no payment|volunteer only|bounty program is closed)\b', re.I)

def discover_paid_issues(theme='Paid bounty', days=30, limit=15):
    if theme not in QUERIES: raise ValueError('Unknown search theme')
    if not 1 <= int(limit) <= 30: raise ValueError('Limit must be 1–30')
    after = (datetime.now(timezone.utc)-timedelta(days=int(days))).date().isoformat()
    query = QUERIES[theme] + f' created:>={after}'
    response = requests.get('https://api.github.com/search/issues', params={'q':query,'sort':'created','order':'desc','per_page':min(100,int(limit)*4)},
        headers={'Accept':'application/vnd.github+json','User-Agent':'AgentForge-Growth-Engine/0.8'},timeout=25)
    if response.status_code in (403,429): raise RuntimeError('GitHub rate limit or access restriction. Try later.')
    response.raise_for_status()
    items=[]
    for issue in response.json().get('items',[]):
        if issue.get('pull_request') or issue.get('state')!='open': continue
        title=str(issue.get('title') or '')
        body=str(issue.get('body') or '')[:10000]
        content=title+'\n'+body
        if not MONEY.search(content) or NEGATIVE.search(content): continue
        url=issue.get('html_url','')
        if not url.startswith('https://github.com/'): continue
        items.append({'source_id':'github-paid:'+str(issue.get('id')),
            'title':title[:300], 'description':body[:5000], 'body':body[:5000],
            'source_url':url, 'application_url':'', 'external_url':'',
            'budget':'', 'contract_type':'', 'location':'',
            'published_at':str(issue.get('created_at') or ''),
            'category':'GitHub funded signal (unverified)',
            'review_note':'UNVERIFIED. Public GitHub issue with money/bounty wording; not evidence of a payable contract.\nDescription: '+body[:2500]})
        if len(items)>=limit: break
    return items
