"""Conservative post-generation review. Heuristics flag risks; not a factual guarantee."""
import re

BUYER_PATTERNS = (
    r'\bwe are (seeking|looking for|hiring|recruiting) (your expertise|a developer|developers|an engineer|engineers|a freelancer)\b',
    r'\bplease (apply|submit your (application|proposal|resume|cv)|send (us|your) (a |your )?(resume|cv))\b',
    r'\bwe (need|require) (a |an )?(developer|engineer|freelancer) (to|who)\b',
    r'\bjoin our (team|company)\b',
)
SENDER_PATTERNS = (
    r'\b(we|our team) (can|could|would be happy to|help|offer|provide|speciali[sz]e|build|develop|support|assist)\b',
    r'\b(i|we) (would like to|wanted to) (offer|help|discuss|explore|share)\b',
    r'\b(our|my) (services|expertise|approach|experience|team)\b',
)
OVERCLAIM_PATTERNS = (
    r'\b(we noticed|we know|it is clear) (that )?you (are hiring|need to hire|have a budget)\b',
    r'\byou (are|have been) (actively )?(seeking|looking for|hiring) (a |an )?(developer|engineer|agency)\b',
    r'\b(guaranteed results|100% guaranteed)\b',
)
def review_proposal(draft):
    """Never approves facts, only identifies common draft failure modes."""
    body=str(draft or '').strip()
    reasons=[]
    if len(body)<50:
        reasons.append('Draft is empty or too short.')
    if any(re.search(p,body,re.I) for p in BUYER_PATTERNS):
        reasons.append('Buyer/seller role reversal or job-ad language detected.')
    if not any(re.search(p,body,re.I) for p in SENDER_PATTERNS):
        reasons.append('Sender as service provider is not clearly expressed.')
    if any(re.search(p,body,re.I) for p in OVERCLAIM_PATTERNS):
        reasons.append('Possible unsupported claim about buyer intent or results.')
    return {'needs_revision':bool(reasons),'reasons':reasons,
            'human_review_required':True,
            'facts_verified':False}
def generate_reviewed_draft(generator,prompt,*,max_attempts=2):
    """At most one correction attempt. Never sends or persists content."""
    from lead_qualification import draft_prompt  # imported for consistent module availability
    response=''
    review=None
    for attempt in range(max_attempts):
        request=prompt if attempt==0 else (
            prompt+'\n\nCORRECTION: Your previous output was rejected: '+
            '; '.join(review['reasons'])+
            '\nWrite as OUR software services team offering services TO the prospect. '
            'Do not write as the prospect seeking developers. Do not invent facts. '
            'Write a fresh, complete draft.'
        )
        response=generator(request)
        review=review_proposal(response)
        if not review['needs_revision']:
            break
    return {'draft':response,'review':review,'attempts':attempt+1}
