"""Conservative, explainable ranking of unverified Freelancer listings.

No exchange-rate conversion. Hourly rates are not total project budgets.
"""
import re

SKILLS = {
    'AI / Automation': r'\b(?:llm|rag|chatbot|machine learning|ai agent|ai assistant|artificial intelligence|make\.com automation|n8n automation|workflow automation)\b',
    'Python / Backend': r'\b(?:python|fastapi|django|flask|backend|back.end|rest api|api integration|postgresql)\b',
    'Full-stack / Web': r'\b(?:react|next\.?js|vue\.?js|full.stack|web app|web application|saas|laravel|node\.?js)\b',
    'DevOps / Cloud': r'\b(?:docker|kubernetes|terraform|ci/cd|devops engineer|devops pipeline|aws deployment|server hardening|cloud infrastructure)\b',
    'Cybersecurity': r'\b(?:penetration test|pentest|vulnerability assessment|security audit|os hardening|security hardening)\b',
    'Data / Scraping': r'\b(?:web scraping|data extraction|data pipeline|etl|data analysis|data engineer|pandas)\b',
}
NON_ENGINEERING = re.compile(r'\b(?:lead generation|linkedin engagement|social media marketing|seo campaign|sales outreach|cold calling|logo design|graphic design|virtual assistant|data entry|appointment setting|content writing|video editing)\b', re.I)
TECH_DELIVERABLE = re.compile(r'\b(?:build|develop|implement|integrat(?:e|ion)|debug|fix|deploy|automate|create an api|create a dashboard|software|application|script|code|backend|database|pipeline|system)\b', re.I)
CURRENCY = re.compile(r'^\s*([\d,.]+|\?)\s*[–-]\s*([\d,.]+|\?)\s+([A-Z]{3})\s*$')

def rank_project(item, min_fixed_usd=250):
    title = str(item.get('title') or '')[:300]
    desc = str(item.get('description') or '')[:4000]
    title_matches = [name for name, pat in SKILLS.items() if re.search(pat, title, re.I)]
    body_matches = [name for name, pat in SKILLS.items() if re.search(pat, desc, re.I)]
    matches = list(dict.fromkeys(title_matches + body_matches))
    nontech = bool(NON_ENGINEERING.search(title))
    deliverable = bool(TECH_DELIVERABLE.search(title + ' ' + desc))
    reasons = []
    score = 10
    if title_matches:
        score += 35
        reasons.append('Technical skill appears in title')
    elif body_matches:
        score += 15
        reasons.append('Technical skill appears only in description; check relevance')
    else:
        reasons.append('No clear technical skill match')
    if deliverable:
        score += 15
        reasons.append('Possible engineering deliverable (unverified)')
    else:
        reasons.append('No clear engineering deliverable')
    kind = str(item.get('contract_type') or '').lower().strip()
    if kind == 'fixed':
        score += 10
        reasons.append('Fixed-price listing')
    elif kind == 'hourly':
        score += 5
        reasons.append('Hourly listing; rate is not total budget')
    else:
        reasons.append('Contract type unknown')
    raw_budget = str(item.get('budget') or '')
    parsed = CURRENCY.match(raw_budget)
    budget_min = budget_max = None
    currency = ''
    if parsed:
        currency = parsed.group(3)
        try:
            budget_min = float(parsed.group(1).replace(',','')) if parsed.group(1) != '?' else None
            budget_max = float(parsed.group(2).replace(',','')) if parsed.group(2) != '?' else None
        except ValueError:
            pass
    if kind == 'fixed' and currency == 'USD':
        if budget_max is not None and budget_max < min_fixed_usd:
            score -= 25
            reasons.append(f'Fixed-price maximum ${budget_max:g} below ${min_fixed_usd} threshold')
        elif budget_min is not None and budget_min >= min_fixed_usd:
            score += 20
            reasons.append('Fixed-price minimum meets USD threshold')
        else:
            score += 5
            reasons.append('USD fixed-price range overlaps threshold; actual value uncertain')
    elif kind == 'hourly':
        reasons.append('Hourly rate not compared with fixed-project budget')
    else:
        reasons.append('Currency not converted; budget requires manual assessment')
    if nontech:
        score = min(score, 25)
        reasons.append('Non-engineering task in title: hard cap')
    if not matches:
        score = min(score, 30)
    if not deliverable:
        score = min(score, 45)
    score = max(0, min(100, score))
    return {'score': score, 'priority': 'High review' if score >= 75 else ('Review' if score >= 50 else 'Low'),
            'services': matches, 'reasons': reasons, 'budget_currency': currency,
            'budget_min': budget_min, 'budget_max': budget_max, 'kind': kind}
