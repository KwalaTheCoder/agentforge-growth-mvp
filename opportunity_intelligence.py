"""Explainable, conservative issue triage. Not a payment/contract verifier."""
import re

DELIVERED = re.compile(r"\b(?:implements?|implemented|completed|delivered|shipped|merged|14/14 unit tests passing)\b", re.I)
PR = re.compile(r"(?:pull request\s*:\s*#\d+|github\.com/[^\s]+/pull/\d+|\bPR\s*#\d+)", re.I)
PAYOUT = re.compile(r"\b(?:bounty proposal|designated payout rail|payout address|requesting payout)\b", re.I)
CLAIMED = re.compile(r"\b(?:already claimed|bounty claimed|assigned to|work completed|task completed)\b", re.I)
INVITE = re.compile(r"\b(?:open for applicants|applications? (?:are )?open|looking for (?:a |an )?(?:[\w-]+ )?(?:developer|contractor|freelancer|contributor)|seeking (?:a |an )?(?:developer|contractor|freelancer)|available to claim|unclaimed bounty|apply to (?:work|claim))\b", re.I)
CURRENCY = re.compile(r"(?:[$€£]\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:USD|USDC|EUR|GBP)\b)", re.I)
PAY_TERMS = re.compile(r"\b(?:bounty|reward|paid task|paid work|payment offered|budget|compensation)\b", re.I)
NEGATED = re.compile(r"\b(?:not funded yet|unfunded|funding pending|not yet funded|awaiting funding)\b", re.I)

def analyze_issue(issue):
    title=str(issue.get('title') or '')[:500]
    body=str(issue.get('body') or issue.get('excerpt') or '')[:50000]
    text=title+'\n'+body
    state=str(issue.get('state') or '').lower()
    evidence=[]; concerns=[]
    if state=='closed':
        concerns.append('Issue is closed')
        return _result('Not an Opportunity','Closed issue',evidence,concerns)
    if DELIVERED.search(body) and PR.search(body) and PAYOUT.search(text):
        concerns.append('Existing PR, delivered work and payout request')
        return _result('Not an Opportunity','Author is seeking payout for prior work',evidence,concerns)
    if CLAIMED.search(text):
        concerns.append('Claimed/completed language detected; context requires review')
        return _result('Research Candidate','Possible existing claim',evidence,concerns)
    if re.search(r'\bbounty proposal\b',title,re.I):
        concerns.append('Proposal awaiting approval, not a confirmed open assignment')
        return _result('Research Candidate','Bounty proposal is not an open offer',evidence,concerns)
    invited=bool(INVITE.search(text))
    has_pay=bool(CURRENCY.search(text) and PAY_TERMS.search(text))
    if invited: evidence.append('Explicit invitation to new applicants or claimants')
    if has_pay: evidence.append('Amount and paid-work terminology present')
    if NEGATED.search(text): concerns.append('Text explicitly indicates unfunded or pending funding')
    if state!='open': concerns.append('Open issue state not confirmed')
    if invited and has_pay and state=='open' and not NEGATED.search(text):
        return _result('Actionable Opportunity','Open invitation and amount detected; verify terms manually',evidence,concerns)
    if invited or has_pay:
        return _result('Research Candidate','One or more eligibility/payment requirements remain unclear',evidence,concerns)
    concerns.append('No explicit paid invitation supported by the issue text')
    return _result('Not an Opportunity','No actionable paid-work evidence',evidence,concerns)

def _result(label,reason,evidence,concerns):
    return {'intelligence_label':label,'intelligence_reason':reason,
            'positive_signals':'; '.join(evidence) or 'None detected',
            'risk_flags':'; '.join(concerns) or 'Funding, eligibility and terms remain unverified',
            'commercially_verified':False,'manual_review_required':True}
