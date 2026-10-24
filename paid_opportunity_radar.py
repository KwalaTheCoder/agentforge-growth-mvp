"""Read-only GitHub opportunity research. Never certifies payment or authorizes outreach."""
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests

SEARCHES = [
    'is:issue is:open "paid bounty"',
    'is:issue is:open label:bounty language:Python',
    'is:issue is:open "bounty" "API"',
    'is:issue is:open "bounty" "AI"',
]
SKILLS = {
    'Python': ('python', 'pytest', 'pandas', 'fastapi', 'django', 'flask'),
    'Automation': ('automation', 'workflow', 'scraping', 'integration', 'github actions', 'ci/cd'),
    'AI': ('llm', 'ai agent', 'agentic', 'rag', 'ollama', 'openai', 'machine learning'),
    'Backend/API': ('api', 'backend', 'endpoint', 'database', 'postgres', 'typescript', 'nodejs'),
}
RED_FLAGS = ('archived duplicate', 'historical snapshot', 'not a current invitation',
             'unavailable to new', 'already claimed', 'do not claim', 'verification-unavailable',
             'not currently executable', 'closed to submissions')
PAYMENT = re.compile(r'(?:\$\s*|\busd\s*|\busdc\s*|€\s*|\beur\s*)(\d[\d,]*(?:\.\d+)?)', re.I)
REWARD_CONTEXT = re.compile(r'\b(?:bounty|reward|payout|compensation|budget|paid|payment|prize|funded)\b', re.I)
TASK_CONTEXT = re.compile(r'\b(?:implement|fix|add|build|develop|integrate|support|refactor|write|create|deliver|acceptance criteria|deliverable|task|contributor|pull request|submit a pr)\b', re.I)
NON_OPPORTUNITY = re.compile(r'\b(?:seller submission|introductions:|income opportunity registry|dependency dashboard|vulnerability tracker|relay log|revenue lanes|bounty alert|bounty scan results|new opportunit(?:y|ies) found|independent .* ledger ready|reverse bounty|test bounty)\b', re.I)
MIRROR_HINTS = ('source url', 'original link', '原始链接', 'bounty-plaza')
GITHUB_ISSUE_URL = re.compile(r'https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/(\d+)', re.I)
SOURCE_LINK = re.compile(r'(?im)^\s*(?:[-*>]\s*)?(?:source\s*(?:url|link)|original\s*(?:url|link|issue)|原始链接)\s*[:：]\s*(https://github\.com/[^\s)<>]+)')
REWARD_AMOUNT = re.compile(r'(?<![\w])(?:\$\s*([0-9][\d,]*(?:\.\d+)?)\s*(?:USD|USDC)?|([0-9][\d,]*(?:\.\d+)?)\s*(?:USD|USDC)\b)', re.I)
REWARD_LINE = re.compile(r'\b(?:reward|bounty|payout|compensation|budget|prize|worker price|funding)\b', re.I)
COMPLETED = re.compile(r'\b(?:slots?:?\s*\d+\s*\(filled\)|status:\s*(?:delivered|completed|claimed)|already (?:delivered|completed|claimed)|payout (?:received|completed))\b', re.I)


def _contains(text, phrase):
    return bool(re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', text, re.I))


def _days(iso, now=None):
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, ((now or datetime.now(timezone.utc)) - dt).days)
    except (ValueError, TypeError, AttributeError):
        return 9999


def evaluate(issue, now=None):
    title = str(issue.get('title') or '')
    body = str(issue.get('body') or '')[:12000]
    text = title + '\n' + body
    labels = [str(x.get('name', '')).lower() for x in (issue.get('labels') or []) if isinstance(x, dict)]
    label_text = ' '.join(labels)
    age = _days(issue.get('updated_at'), now)
    matches = [name for name, words in SKILLS.items() if any(_contains(text, w) or _contains(label_text, w) for w in words)]
    flags = [flag for flag in RED_FLAGS if flag in text.lower() or flag in label_text]
    if issue.get('state') != 'open': flags.append('not open')
    if 'pull_request' in issue: flags.append('pull request, not issue')
    if issue.get('assignee') or issue.get('assignees'): flags.append('assigned; check availability')
    if age > 180: flags.append('not updated in 180+ days')
    if not matches: flags.append('no demonstrated skill match')

    # Money elsewhere in an issue (product pricing, crypto routes, example data) is not a bounty.
    reward_lines = [line for line in text.splitlines() if REWARD_LINE.search(line) or REWARD_LINE.search(title)]
    payment_mentions = []
    for line in reward_lines:
        for m in REWARD_AMOUNT.finditer(line):
            amount = next((g for g in m.groups() if g), '')
            if amount and float(amount.replace(',', '')) > 0 and amount not in payment_mentions:
                payment_mentions.append(amount)
    payment_mentions = payment_mentions[:5]
    reward_label = any(_contains(l, 'paid') or _contains(l, 'funded') for l in labels)
    reward_title = bool(re.search(r'\b(?:bounty|reward|paid task)\b', title, re.I))
    payment_signal = bool(payment_mentions or reward_label or _contains(text, 'paid bounty'))
    if not payment_signal: flags.append('no explicit monetary evidence')

    task_signal = bool(TASK_CONTEXT.search(title) or (TASK_CONTEXT.search(body) and (reward_title or 'bounty' in label_text)))
    if not task_signal: flags.append('no explicit work request')
    if NON_OPPORTUNITY.search(title) or re.search(r'(?im)^#{2,4}\s*active bounty scan results', body):
        flags.append('not a hiring or bounty request')
    if COMPLETED.search(body) or 'delivered' in labels or 'completed' in labels:
        flags.append('already delivered/completed; not available')
    if re.search(r'\b(?:proposed|proposal)\b', title, re.I) and 'approved' not in text.lower():
        flags.append('proposed reward; not approved')
    is_mirror = any(hint in text.lower() for hint in MIRROR_HINTS) and ('source url' in text.lower() or '原始链接' in text)
    if is_mirror: flags.append('aggregator/mirror; verify original issue')
    source_match = SOURCE_LINK.search(body) if is_mirror else None
    original_url = source_match.group(1).rstrip('.,;') if source_match else None
    if is_mirror and not original_url:
        flags.append('mirror has no machine-readable original issue link')
    if payment_signal and not payment_mentions: flags.append('reward amount not established')

    evidence = 'Payment claim (unverified)' if payment_signal else 'No task reward evidence'
    if 'claimable-live' in label_text and 'claimed-live' not in label_text:
        evidence = 'Claimable label (unverified)'
    score = min(100, 12 * len(matches) + (20 if age <= 30 else 10 if age <= 90 else 0)
                + (20 if payment_signal else 0) + (15 if task_signal else 0))
    blockers = ('not open', 'pull request, not issue', 'assigned; check availability',
                'no demonstrated skill match', 'no explicit monetary evidence',
                'no explicit work request', 'not a hiring or bounty request',
                'already delivered/completed; not available', 'proposed reward; not approved')
    if any(f in flags for f in blockers) or any(f in flags for f in RED_FLAGS):
        score = min(score, 35)
    elif is_mirror:
        score = min(score, 50)
    status = 'Review manually' if score >= 55 and not flags else 'Hold / verify' if score >= 25 else 'Skip'
    repo_url = str(issue.get('repository_url') or '')
    return {
        'title': title, 'url': issue.get('html_url', ''), 'original_url': original_url, 'repo': repo_url.rsplit('/', 2)[-2:],
        'score': score, 'status': status, 'skill_matches': matches,
        'payment_evidence': evidence, 'amount_mentions_unverified': payment_mentions,
        'age_days_since_update': age, 'red_flags': flags, 'labels': labels,
        'description_excerpt': body[:1800],
        'qualification': 'Human verification required',
        'verification': {'state': 'not_checked', 'checked_url': None, 'notes': []},
        'outreach_approved': False,
        'competition': {'state': 'not_checked', 'linked_pr_count': None, 'claim_comment_count': None, 'evidence_urls': []},
    }


def _github_get(url, headers, timeout):
    """Return (JSON, error). Missing evidence is never treated as zero competition."""
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json(), None
    except (requests.RequestException, ValueError) as exc:
        return None, str(exc)[:200]


def _verify_issue(item, headers, timeout=12):
    """Verify the canonical issue directly; 404/403/network failure never means available."""
    target = item.get('original_url') or item.get('url') or ''
    result = {'state': 'unknown', 'checked_url': target, 'notes': []}
    match = GITHUB_ISSUE_URL.fullmatch(target)
    if not match:
        result['state'] = 'blocked'
        result['notes'].append('Missing or invalid original GitHub issue URL')
        return result, None, None
    owner, repo, number = match.groups()
    base = f'https://api.github.com/repos/{owner}/{repo}/issues/{number}'
    issue, err = _github_get(base, headers, timeout)
    if err or not isinstance(issue, dict):
        if err and ('404' in err or '410' in err):
            result['state'] = 'blocked'
        result['notes'].append('Original issue could not be verified: ' + (err or 'invalid response'))
        return result, None, base
    if 'pull_request' in issue:
        result['state'] = 'blocked'
        result['notes'].append('URL resolves to a pull request')
    elif issue.get('state') != 'open':
        result['state'] = 'blocked'
        result['notes'].append('Original issue is not open')
    elif issue.get('assignee') or issue.get('assignees'):
        result['state'] = 'blocked'
        result['notes'].append('Original issue already assigned')
    else:
        result['state'] = 'open_unassigned'
    return result, issue, base


def _competition_check(item, headers, timeout=12, base=None):
    """Sample the first 100 timeline events/comments; incomplete != zero competition."""
    result = {'state': 'unknown', 'linked_pr_count': None, 'claim_comment_count': None,
              'evidence_urls': [], 'notes': []}
    if not base:
        verified, issue, base = _verify_issue(item, headers, timeout)
        if verified['state'] != 'open_unassigned':
            result['state'] = 'blocked' if verified['state'] == 'blocked' else 'unknown'
            result['notes'].extend(verified['notes'])
            return result
    result['evidence_urls'].append(item.get('original_url') or item.get('url'))
    timeline, terr = _github_get(base + '/timeline?per_page=100', headers, timeout)
    if isinstance(timeline, list):
        prs = set()
        for event in timeline:
            source_issue = ((event.get('source') or {}).get('issue') or {})
            if 'pull_request' in source_issue and source_issue.get('html_url'):
                prs.add(source_issue['html_url'])
            if event.get('event') == 'connected' and (event.get('subject') or {}).get('type') == 'pull_request':
                result['notes'].append('Connected PR event observed')
        result['linked_pr_count'] = len(prs)
        result['evidence_urls'].extend(sorted(prs)[:10])
        if prs:
            result['state'] = 'competition_detected'
            result['notes'].append('Cross-referenced PR(s) observed; check relevance')
        if len(timeline) == 100:
            result['notes'].append('Timeline truncated at 100 events')
    else:
        result['notes'].append('Timeline unavailable: ' + (terr or 'invalid response'))
    comments, cerr = _github_get(base + '/comments?per_page=100', headers, timeout)
    if isinstance(comments, list):
        claim_pattern = re.compile(r"(?i)(?:\b(?:i(?:’|')?ll|i will|i am|i’m|working on|claimed|/claim|submitted|opened a pr)\b.{0,50}\b(?:work|issue|task|this|pr)\b|^\s*/claim\b)")
        claims = [c for c in comments if claim_pattern.search(c.get('body') or '')]
        result['claim_comment_count'] = len(claims)
        result['evidence_urls'].extend(c.get('html_url') for c in claims[:10] if c.get('html_url'))
        if claims:
            result['state'] = 'competition_detected'
            result['notes'].append('Possible claim comments; manual review required')
        if len(comments) == 100:
            result['notes'].append('Comments truncated at 100')
    else:
        result['notes'].append('Comments unavailable: ' + (cerr or 'invalid response'))
    if result['state'] == 'unknown' and result['linked_pr_count'] is not None and result['claim_comment_count'] is not None:
        result['state'] = 'no_signals_in_sample'
        result['notes'].append('No competition signal in sampled data; availability not guaranteed')
    return result


def _validate_candidate(item, headers, timeout):
    verification, original, base = _verify_issue(item, headers, timeout)
    item['verification'] = verification
    if verification['state'] != 'open_unassigned':
        item['red_flags'].append('original issue not verified open and unassigned')
        item['status'] = 'Skip' if verification['state'] == 'blocked' else 'Hold / verify'
        item['score'] = min(item['score'], 20 if verification['state'] == 'blocked' else 45)
        return
    # The mirror's advertised bounty is not proof of reward on the original issue.
    if item.get('original_url'):
        original_eval = evaluate(original)
        item['payment_evidence'] = 'Mirror payment claim (unverified)'
        item['amount_mentions_unverified'] = original_eval['amount_mentions_unverified']
        if not original_eval['amount_mentions_unverified']:
            item['red_flags'].append('original issue has no explicit numeric bounty')
            item['status'] = 'Hold / verify'
            item['score'] = min(item['score'], 45)
    comp = _competition_check(item, headers, timeout, base=base)
    item['competition'] = comp
    if comp['state'] == 'competition_detected':
        item['red_flags'].append('competition detected on original issue')
        item['status'] = 'Hold / verify'
        item['score'] = min(item['score'], 50)
    elif comp['state'] == 'unknown':
        item['red_flags'].append('competition check incomplete')
        item['status'] = 'Hold / verify'
        item['score'] = min(item['score'], 50)
    # A clean sample only allows manual review, never payment certification.
    if item['status'] == 'Review manually':
        item['qualification'] = 'Original open/unassigned; sampled competition clean; reward still unverified'

def discover(max_per_query=15, token=None, timeout=18, competition_limit=5):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'AgentForge-Paid-Radar/1.3',
               'X-GitHub-Api-Version': '2022-11-28'}
    if token: headers['Authorization'] = 'Bearer ' + token
    unique, errors = {}, []
    for query in SEARCHES:
        try:
            response = requests.get('https://api.github.com/search/issues',
                params={'q': query, 'sort': 'updated', 'order': 'desc', 'per_page': max_per_query},
                headers=headers, timeout=timeout)
            response.raise_for_status()
            for issue in response.json().get('items', []):
                url = issue.get('html_url', '')
                if urlparse(url).hostname == 'github.com' and url not in unique:
                    unique[url] = issue
        except (requests.RequestException, ValueError) as exc:
            errors.append({'query': query, 'error': str(exc)[:250]})
    ranked = sorted((evaluate(issue) for issue in unique.values()), key=lambda x: x['score'], reverse=True)
    # Verify top plausible candidates, including mirrors that were previously held.
    candidates = [x for x in ranked if x['status'] != 'Skip' and
                  (x['score'] >= 40 or x.get('original_url'))]
    for item in candidates[:max(0, min(competition_limit, 20))]:
        _validate_candidate(item, headers, min(timeout, 12))
    ranked.sort(key=lambda x: x['score'], reverse=True)
    return {'generated_at': datetime.now(timezone.utc).isoformat(), 'opportunities': ranked,
            'errors': errors,
            'disclaimer': 'Only the top candidates are checked against their original GitHub issue. Competition checks are bounded and incomplete. All payments and opportunities are unverified. Never auto-send outreach. Verify original issue, eligibility, scope, reward and contact basis.'}
