"""Freelancer official API project discovery. No scraping or automated bidding."""
from datetime import datetime, timezone
from urllib.parse import urlparse
import re
import requests

API = 'https://www.freelancer.com/api/projects/0.1/projects/active/'
KEYWORDS = re.compile(r'\b(python|fastapi|django|backend|back.end|api|automation|ai|llm|machine learning|chatbot|react|nextjs|next.js|full.stack|devops|docker|kubernetes|cloud|cybersecurity|security|scraping|data|node.js|php|laravel|vue)\b', re.I)


def fetch_projects(query, token, limit=30, minimum_budget=0, only_relevant=True):
    """Fetch active project listings from the official endpoint; no undocumented fallback."""
    query = (query or '').strip()
    if not query or len(query) > 120:
        raise ValueError('Enter a search term of 1–120 characters.')
    limit = max(1, min(int(limit), 100))
    params = {'query': query, 'limit': limit, 'full_description': 'true'}
    headers = {'Accept': 'application/json', 'User-Agent': 'AgentForgeGrowthEngine/1.0'}
    if token.strip():
        headers['Authorization'] = 'Bearer ' + token.strip()
    try:
        response = requests.get(API, params=params, headers=headers, timeout=35)
    except requests.RequestException as exc:
        raise RuntimeError('Freelancer API connection failed: ' + str(exc)) from exc
    if response.status_code in (401, 403):
        raise RuntimeError(f'Freelancer API returned HTTP {response.status_code}. Check OAuth token, permissions, and API access. No scraping fallback is used.')
    if not response.ok:
        raise RuntimeError(f'Freelancer API returned HTTP {response.status_code}: {response.text[:350]}')
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError('Freelancer API returned non-JSON content.') from exc
    if not isinstance(payload, dict):
        raise RuntimeError('Unexpected Freelancer API response.')
    if payload.get('status') == 'error':
        raise RuntimeError('Freelancer API error: ' + str(payload.get('message') or payload.get('error_code') or 'unknown'))
    result = payload.get('result') or {}
    projects = result.get('projects') if isinstance(result, dict) else None
    if not isinstance(projects, list):
        raise RuntimeError('Freelancer API response has no projects list; endpoint/permissions may have changed.')
    items = []
    for p in projects:
        if not isinstance(p, dict):
            continue
        title = str(p.get('title') or '').strip()
        desc = str(p.get('description') or p.get('preview_description') or '').strip()
        if not title:
            continue
        if only_relevant and not KEYWORDS.search(title + ' ' + desc):
            continue
        budget = p.get('budget') or {}
        minimum = budget.get('minimum') if isinstance(budget, dict) else None
        maximum = budget.get('maximum') if isinstance(budget, dict) else None
        try:
            if minimum_budget and maximum is not None and float(maximum) < minimum_budget:
                continue
        except (TypeError, ValueError):
            pass
        currency = p.get('currency') or {}
        code = currency.get('code', '') if isinstance(currency, dict) else ''
        amount = f'{minimum if minimum is not None else "?"}–{maximum if maximum is not None else "?"} {code}'.strip()
        seo = str(p.get('seo_url') or '').strip().lstrip('/')
        if seo and not seo.startswith('http'):
            url = 'https://www.freelancer.com/projects/' + seo.removeprefix('projects/')
        else:
            url = str(p.get('url') or '')
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname not in ('freelancer.com', 'www.freelancer.com'):
            continue
        pid = str(p.get('id') or '')
        if not pid:
            continue
        timestamp = p.get('time_submitted')
        try:
            published = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat() if timestamp else ''
        except (ValueError, TypeError, OverflowError, OSError):
            published = ''
        item = {
            'source_id': 'freelancer:' + pid, 'title': title[:300],
            'source_url': url, 'external_url': url, 'published_at': published,
            'category': 'Freelancer API — unverified', 'description': desc[:4000],
            'budget': amount, 'contract_type': str(p.get('type') or ''),
            'location': 'Not verified',
            'review_note': 'UNVERIFIED Freelancer.com API listing.\n'
                           'Budget range (not guaranteed): ' + amount + '\n'
                           'Project type: ' + str(p.get('type') or '') + '\n'
                           'Description: ' + desc[:2500] + '\n'
                           'Verify project status, platform eligibility, payment and application rules before bidding.'
        }
        items.append(item)
    return items
