"""Evidence-based public company research. Not proof of buyer intent."""
import ipaddress
import re
import socket
from collections import Counter
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import requests

API='https://api.github.com'
HEADERS={'Accept':'application/vnd.github+json','User-Agent':'AgentForge-Research/1.5'}

class PageText(HTMLParser):
    def __init__(self):
        super().__init__(); self.title=''; self.text=[]; self._title=False; self._ignore=0; self.description=''
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript'): self._ignore+=1
        if tag=='title': self._title=True
        if tag=='meta':
            a=dict(attrs)
            if a.get('name','').lower()=='description': self.description=a.get('content','')[:350]
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript'): self._ignore=max(0,self._ignore-1)
        if tag=='title': self._title=False
    def handle_data(self,data):
        if self._ignore: return
        if self._title: self.title+=data
        elif len(self.text)<300: self.text.append(data)

def github_research(github_url, max_repos=8):
    u=urlparse(str(github_url))
    if u.scheme!='https' or u.hostname!='github.com': raise ValueError('Expected github.com organization URL')
    login=u.path.strip('/')
    if not re.fullmatch(r'[A-Za-z0-9-]{1,39}',login): raise ValueError('Invalid organization login')
    resp=requests.get(f'{API}/orgs/{login}/repos',headers=HEADERS,
                      params={'sort':'pushed','direction':'desc','per_page':max_repos},timeout=20)
    if resp.status_code in (403,429): raise RuntimeError('GitHub API rate limit; retry later')
    resp.raise_for_status(); data=resp.json()
    if not isinstance(data,list): raise ValueError('Unexpected GitHub response')
    repos=[]; languages=Counter(); active=0
    for r in data:
        if r.get('fork') or r.get('archived'): continue
        lang=r.get('language')
        if lang: languages[lang]+=1
        pushed=str(r.get('pushed_at') or '')
        try:
            dt=datetime.fromisoformat(pushed.replace('Z','+00:00'))
            if (datetime.now(timezone.utc)-dt).days<=90: active+=1
        except ValueError: pass
        repos.append({'name':r.get('name',''), 'url':r.get('html_url',''),
                      'description':str(r.get('description') or '')[:220],
                      'language':lang or 'Unknown','pushed_at':pushed,
                      'open_issues_count':r.get('open_issues_count',0)})
    return {'repos':repos,'languages':languages.most_common(6),'active_90d':active,
            'evidence':[{'claim':'Public repository uses '+str(r['language']),
                         'url':r['url'],'kind':'technical'} for r in repos if r['language']!='Unknown'][:8],
            'buyer_need_verified':False}

def _public_host(host):
    if not host or host.lower()=='localhost' or host.endswith(('.local','.internal','.localhost')): return False
    try:
        records=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
        addresses={ipaddress.ip_address(rec[4][0]) for rec in records}
        return bool(addresses) and all(x.is_global for x in addresses)
    except (socket.gaierror,ValueError): return False

def website_research(url):
    """Only HTTPS public host, robots permission, homepage; no redirects or arbitrary paths."""
    parsed=urlparse(str(url).strip())
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None,443):
        raise ValueError('Use a public HTTPS company homepage')
    if parsed.path not in ('','/') or parsed.query or parsed.fragment:
        raise ValueError('Only homepage URLs supported')
    host=parsed.hostname.lower()
    if not _public_host(host): raise ValueError('Host is not publicly routable')
    root='https://'+host
    robots=requests.get(root+'/robots.txt',headers={'User-Agent':'AgentForge-Research/1.5'},timeout=8,allow_redirects=False)
    if robots.status_code in (301,302,303,307,308): raise ValueError('Robots redirect: website skipped')
    if robots.status_code in (401,403,429) or robots.status_code>=500: raise ValueError('Cannot verify robots permission; website skipped')
    if robots.status_code==200:
        rp=RobotFileParser();rp.parse(robots.text[:100000].splitlines())
        if not rp.can_fetch('AgentForge-Research',root+'/'): raise ValueError('robots.txt disallows homepage')
    resp=requests.get(root+'/',headers={'User-Agent':'AgentForge-Research/1.5','Accept':'text/html'},timeout=12,
                      allow_redirects=False,stream=True)
    try:
        if resp.status_code in (301,302,303,307,308): raise ValueError('Website redirects; manually verify final homepage')
        resp.raise_for_status()
        if 'text/html' not in resp.headers.get('Content-Type',''): raise ValueError('Not an HTML homepage')
        size=0;chunks=[]
        for part in resp.iter_content(chunk_size=8192):
            size+=len(part)
            if size>150000: break
            chunks.append(part)
        html=b''.join(chunks).decode(resp.encoding or 'utf-8',errors='replace')
    finally: resp.close()
    parser=PageText();parser.feed(html)
    text=' '.join(parser.text)
    text=re.sub(r'\s+',' ',unescape(text)).strip()[:700]
    return {'url':root+'/', 'title':unescape(parser.title).strip()[:180],
            'description':unescape(parser.description).strip()[:350],
            'excerpt':text, 'buyer_need_verified':False}

def score_research(detail,github=None,website=None,operator_evidence=''):
    technical=0; reasons=[]
    if github:
        technical+=20 if github['repos'] else 0
        technical+=15 if github['active_90d'] else 0
        if github['languages']: technical+=10
        reasons.append('Public repository activity shows technical fit, not buying intent')
    if website and (website['title'] or website['description']):
        technical+=10;reasons.append('Company homepage retrieved (unverified business need)')
    if detail.get('description'): technical+=10
    verified=bool(operator_evidence.strip())
    return {'technical_fit_score':min(technical,100),
            'buyer_need_status':'Operator-supplied evidence; not independently verified' if verified else 'Unknown — no buying signal established',
            'reasons':reasons,'contact_permission_verified':False}
