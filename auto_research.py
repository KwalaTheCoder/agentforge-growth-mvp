"""Bounded, read-only GitHub research. Findings are NOT commercial qualification."""
from datetime import datetime, timezone
from urllib.parse import urlparse
import re

from direct_b2b import github_profile, discover_public_issue_signals, classify_public_issue, assess_payment_evidence


def github_org_login(source_url):
    p = urlparse(str(source_url or '').strip())
    parts = p.path.strip('/').split('/')
    if p.scheme != 'https' or p.hostname not in ('github.com', 'www.github.com') or len(parts) != 1:
        raise ValueError('Automatic research currently supports only https://github.com/ORG sources.')
    login = parts[0]
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', login):
        raise ValueError('Invalid GitHub organization login.')
    return login


def research_company(source_url, limit=12):
    """Read profile and bounded public issue search; never mutate CRM or send messages."""
    login = github_org_login(source_url)
    profile = github_profile(login)
    issues = discover_public_issue_signals(profile['source_url'], min(max(int(limit), 1), 20))
    findings = []
    for issue in issues['issues']:
        classification = classify_public_issue(issue)
        payment = assess_payment_evidence(issue)
        findings.append({
            'title': issue['title'], 'url': issue['url'],
            'repository': issue['repository'], 'updated_at': issue['updated_at'],
            'technical_signal': classification['category'],
            'funding_signal': payment['funding_status'],
            'excerpt': issue.get('excerpt', '')[:300],
            'commercially_verified': False,
        })
    return {
        'researched_at': datetime.now(timezone.utc).isoformat(),
        'organization': login,
        'profile': profile,
        'profile_source': profile['source_url'],
        'website_status': 'Listed in GitHub profile; not independently verified' if profile.get('website') else 'Not listed',
        'issues': findings,
        'incomplete_results': issues['incomplete_results'],
        'commercial_need_verified': False,
        'contact_permission_verified': False,
        'recommendation': 'Human review required: verify organization identity, explicit external service need, and permitted business contact route. No outreach authorized.',
        'scope': 'GitHub organization profile and a limited sample of open public GitHub issues only; not a full web investigation.',
    }


def evidence_memo(report):
    p = report['profile']
    lines = [
        'READ-ONLY PUBLIC RESEARCH REPORT — NOT BUYER VERIFICATION',
        f"Organization: {report['organization']}",
        f"Checked at (UTC): {report['researched_at']}",
        f"Profile source: {report['profile_source']}",
        f"Profile name: {p.get('company', '')}",
        f"Profile description: {p.get('description', '') or 'Not supplied'}",
        f"Profile-listed website: {p.get('website', '') or 'Not supplied'}",
        f"Website verification: {report['website_status']}",
        f"Public issues sampled: {len(report['issues'])}",
        f"Incomplete GitHub search: {report['incomplete_results']}",
        '', 'PUBLIC TECHNICAL SIGNALS (NOT BUYER INTENT):',
    ]
    for i, issue in enumerate(report['issues'], 1):
        lines += [f"{i}. {issue['title']}", f"   Source: {issue['url']}",
                  f"   Classification: {issue['technical_signal']} / {issue['funding_signal']}"]
    lines += ['', 'Documented paid external service need: NOT VERIFIED',
              'Permitted business contact route: NOT VERIFIED',
              report['recommendation'], report['scope']]
    return '\n'.join(lines)
