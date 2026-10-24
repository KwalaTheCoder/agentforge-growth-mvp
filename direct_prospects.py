"""Public GitHub organization research. Signals are NOT proof of purchase intent."""
from urllib.parse import urlparse
import requests

API = 'https://api.github.com'
HEADERS = {'Accept': 'application/vnd.github+json', 'User-Agent': 'AgentForge-Direct-Prospect-Research/1.4'}


def enrich_github_org(profile):
    """Read one public GitHub org profile; no personal email harvesting."""
    profile_url = str(profile.get('website') or '')
    parsed = urlparse(profile_url)
    if parsed.scheme != 'https' or parsed.hostname != 'github.com':
        raise ValueError('Expected a public github.com organization profile URL')
    login = parsed.path.strip('/')
    if not login or '/' in login or len(login) > 39 or not all(c.isalnum() or c == '-' for c in login):
        raise ValueError('Invalid GitHub organization name')
    response = requests.get(f'{API}/orgs/{login}', headers=HEADERS, timeout=20)
    if response.status_code in (403, 429):
        raise RuntimeError('GitHub API rate limit reached. Try later.')
    response.raise_for_status()
    data = response.json()
    if data.get('type') != 'Organization':
        raise ValueError('Profile is not a GitHub organization')
    website = str(data.get('blog') or '').strip()
    if website and not website.startswith(('https://', 'http://')):
        website = 'https://' + website
    u = urlparse(website)
    if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password:
        website = ''
    description = str(data.get('description') or '').strip()[:500]
    name = str(data.get('name') or login).strip()[:200]
    location = str(data.get('location') or '').strip()[:100]
    notes = ('Public GitHub organization profile; buyer need and outreach permission NOT established.\n'
             f'Public description: {description or "Not supplied"}\n'
             f'Public repositories count: {data.get("public_repos", "Unknown")}\n'
             f'GitHub: https://github.com/{login}\n'
             'Next: independently verify company identity, a relevant business need, and a permitted contact channel.')
    return {
        'company': name, 'country': location, 'website': website or f'https://github.com/{login}',
        'contact': '', 'source': f'https://github.com/{login}',
        'service': 'Python / Backend', 'notes': notes,
        'github_url': f'https://github.com/{login}', 'description': description,
        'company_website': website, 'public_repos': data.get('public_repos', 0),
    }
