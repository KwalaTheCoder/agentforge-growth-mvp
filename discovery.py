"""Conservative public GitHub organization discovery. No scraping or messaging."""
import re
from urllib.parse import urlparse
import requests

API = 'https://api.github.com'
HEADERS = {'Accept': 'application/vnd.github+json', 'User-Agent': 'AgentForge-Growth-Research/0.2'}


def github_orgs(country, keyword='', limit=8):
    """Find public GitHub organizations. These are prospects, NOT verified buyers."""
    country = (country or '').strip()
    keyword = (keyword or '').strip()
    if not country or len(country) > 80 or len(keyword) > 60:
        raise ValueError('Provide a country/location (max 80 chars), keyword max 60 chars.')
    if not re.fullmatch(r"[\w\s.,'()\-]+", country, flags=re.UNICODE):
        raise ValueError('Invalid location characters.')
    q = f'type:org location:"{country}"'
    if keyword:
        q += f' {keyword}'
    with requests.Session() as session:
        session.headers.update(HEADERS)
        resp = session.get(f'{API}/search/users', params={'q': q, 'per_page': min(int(limit), 15)}, timeout=20)
        if resp.status_code in (403, 429):
            raise RuntimeError('GitHub API rate limit reached. Wait until the limit resets; do not retry rapidly.')
        resp.raise_for_status()
        items = resp.json().get('items', [])
        output = []
        for item in items:
            login = item.get('login', '')
            if not login:
                continue
            # Search results already contain an official public profile URL.
            output.append({
                'company': login,
                'country': country,
                'website': item.get('html_url', f'https://github.com/{login}'),
                'contact': '',
                'source': item.get('html_url', f'https://github.com/{login}'),
                'service': 'Python / Backend',
                'notes': 'Public GitHub organization profile. Business identity, country, needs, and permission to contact are NOT verified. Research manually before outreach.',
            })
        return output
