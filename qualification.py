"""Conservative, deterministic guardrails; not a substitute for verifying listings."""
import re

EMPLOYMENT = re.compile(r"\b(staff software engineer|senior software engineer|full[- ]time|permanent position|salaried|employee benefits|employment opportunity|staff engineer)\b", re.I)
CONTRACT = re.compile(r"\b(freelanc(?:e|er)|fixed[- ]price|project[- ]based|paid bounty|contractor needed|seeking (?:a |an )?contractor|paid contract|contract work)\b", re.I)
GEO = re.compile(r"\b(US only|USA only|United States only|must be (?:based|located) in (?:the )?(?:US|USA|United States)|EU only|Europe only|UK only|Canada only|US residents only)\b", re.I)


def apply_guardrails(item, analysis):
    result = dict(analysis)
    title = str(item.get('title') or '')
    body = str(item.get('body') or '')
    text = title + '\n' + body
    employment = bool(EMPLOYMENT.search(title)) or (bool(EMPLOYMENT.search(body)) and not CONTRACT.search(text))
    contract = bool(CONTRACT.search(text))
    if employment and not contract:
        result['classification'] = 'Employment'
        result['score'] = min(int(result.get('score', 0)), 15)
        result['evidence'] = 'Employment wording in listing: ' + (EMPLOYMENT.search(title) or EMPLOYMENT.search(body)).group(0)
        result['uncertainty'] = 'Employment posting; independent contractor eligibility not established.'
    elif result.get('classification') == 'Paid contract signal' and not contract:
        result['classification'] = 'Unclear'
        result['score'] = min(int(result.get('score', 0)), 25)
        result['uncertainty'] = 'No explicit freelance or contract engagement signal; verify manually.'
    location = GEO.search(text)
    result['location_signal'] = location.group(0) if location else 'Not detected (not proof of worldwide eligibility)'
    result['contract_signal'] = bool(contract)
    result['verified'] = False
    return result
