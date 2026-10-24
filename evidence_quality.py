"""Conservative, read-only evidence freshness and GitHub issue rechecks.

Scores indicate which evidence merits manual research, NEVER buyer likelihood.
"""
from datetime import datetime, timezone
from urllib.parse import urlsplit
import re
import requests

API = 'https://api.github.com'
HEADERS = {'Accept': 'application/vnd.github+json', 'User-Agent': 'AgentForge-Evidence-Quality/4.8'}


def _date(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def age_days(value, now=None):
    d = _date(value)
    if not d:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0, (now - d).days)


def issue_locator(url, expected_org):
    p = urlsplit(str(url))
    parts = p.path.strip('/').split('/')
    if (p.scheme != 'https' or p.hostname != 'github.com' or p.port is not None
            or p.username or p.password or p.query or p.fragment or len(parts) != 4
            or parts[0].lower() != str(expected_org).lower() or parts[2] != 'issues'
            or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', parts[1])
            or not re.fullmatch(r'[1-9][0-9]{0,9}', parts[3])):
        raise ValueError('Issue URL must belong to the researched GitHub organization.')
    return f'{API}/repos/{parts[0]}/{parts[1]}/issues/{parts[3]}'


def grade_issue(issue, current=None, now=None):
    """No commercial verification is inferred from issue labels or payment phrases."""
    current = current or {}
    checked = bool(current)
    state = str(current.get('state') or 'Unknown') if checked else 'Not rechecked'
    updated = current.get('updated_at') if checked else issue.get('updated_at')
    days = age_days(updated, now)
    if days is None:
        freshness = 'Unknown'
        points = 0
    elif days <= 90:
        freshness, points = 'Recent (<=90 days)', 40
    elif days <= 365:
        freshness, points = 'Within 1 year', 25
    elif days <= 730:
        freshness, points = '1–2 years old', 10
    else:
        freshness, points = 'Stale (>2 years)', 0
    if checked and state == 'open':
        points += 25
    if checked and state == 'closed':
        points = 0
    if checked and state not in ('open', 'closed'):
        points = min(points, 10)
    if not checked:
        points = min(points, 10)
    # A source URL helps auditing, but does not indicate purchase intent.
    points += 10 if issue.get('url') else 0
    if checked and state == 'closed':
        points = min(points, 10)
    return {
        'title': str(issue.get('title') or '')[:220],
        'url': str(issue.get('url') or ''),
        'last_updated_at': updated or '',
        'age_days': days,
        'freshness': freshness,
        'current_state': state,
        'rechecked': checked,
        'research_priority': min(75, points),
        'funding_signal': str(issue.get('funding_signal') or 'Unknown'),
        'commercial_need_verified': False,
        'contact_permission_verified': False,
        'next_action': ('Review original issue and independently verify scope, funding, and contact route'
                        if checked and state == 'open' else
                        'Do not treat as current demand; check original issue or seek newer evidence'),
    }


def assess_evidence(report, *, recheck=True, limit=12, fetch=None, now=None):
    """Bounded GitHub API requests, partial failures surfaced, no CRM changes."""
    github = report.get('github') or {}
    org = str(github.get('organization') or '').strip()
    issues = list(github.get('issues') or [])[:max(0, min(int(limit), 12))]
    if not org or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', org):
        raise ValueError('Full Company Research must contain a valid GitHub organization.')
    fetch = fetch or requests.get
    rows, errors = [], {}
    for issue in issues:
        current = None
        url = str(issue.get('url') or '')
        if recheck:
            try:
                endpoint = issue_locator(url, org)
                response = fetch(endpoint, headers=HEADERS, timeout=15, allow_redirects=False)
                if response.status_code in (403, 429):
                    raise RuntimeError('GitHub rate limit or access denied')
                response.raise_for_status()
                current = response.json()
                if not isinstance(current, dict) or 'state' not in current:
                    raise ValueError('Unexpected GitHub issue response')
            except (requests.RequestException, RuntimeError, ValueError) as exc:
                errors[url] = str(exc)[:250]
        rows.append(grade_issue(issue, current, now))
    rows.sort(key=lambda x: x['research_priority'], reverse=True)
    return {
        'company': report.get('company', ''), 'assessed_at_utc': (now or datetime.now(timezone.utc)).isoformat(),
        'issues': rows, 'recheck_errors': errors,
        'rechecked_count': sum(row['rechecked'] for row in rows),
        'commercial_need_verified': False, 'contact_permission_verified': False,
        'qualification': 'Research Only — manual verification required',
        'crm_modified': False, 'messages_sent': False,
        'score_meaning': 'Freshness and inspectability for research, NOT probability of purchase',
    }
