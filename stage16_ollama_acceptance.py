"""Stage 16: safe Ollama acceptance check. No CRM writes, no external messages."""
import argparse
import json
import sys
from unittest.mock import patch
from lead_qualification import assess_lead, draft_prompt
from direct_b2b import ollama_generate

TEST_LEAD = {
    'company':'Example Integration Lab (FICTIONAL TEST)',
    'source_url':'https://example.com/',
    'service':'Python / Backend',
    'need_evidence':'FICTIONAL TEST: public request for a FastAPI webhook integration.',
    'evidence_url':'https://example.com/test-request',
    'contact_channel':'FICTIONAL TEST: business inquiry form',
    'identity_checked':True,
    'need_checked':True,
    'contact_permission_checked':True,
}
def run(live=False):
    invalid=dict(TEST_LEAD,need_checked=False)
    assert assess_lead(invalid)['status']=='Needs evidence'
    try:
        draft_prompt(invalid)
    except ValueError:
        print('PASS: incomplete evidence blocks proposal generation')
    else:
        raise AssertionError('Qualification gate was bypassed')
    valid=assess_lead(TEST_LEAD)
    assert valid['status']=='Ready for human outreach review'
    print('PASS: complete fictional fixture unlocks draft generation')
    prompt=draft_prompt(TEST_LEAD)
    with patch('direct_b2b.requests.post') as post:
        post.return_value.status_code=200
        post.return_value.json.return_value={'response':'Hello, this is a fictional test draft.','done_reason':'stop'}
        post.return_value.raise_for_status.return_value=None
        draft=ollama_generate(prompt)
        assert 'fictional test draft' in draft
        assert post.call_args.kwargs['json']['stream'] is False
        print('PASS: mocked Ollama response accepted')
    with patch('direct_b2b.requests.post',side_effect=ConnectionError('simulated offline')):
        try: ollama_generate(prompt)
        except ConnectionError: print('PASS: Ollama offline failure is surfaced')
        else: raise AssertionError('Offline error was swallowed')
    if live:
        print('Calling local Ollama on 127.0.0.1:11434 (no GitHub, no CRM writes)...')
        try:
            response=ollama_generate(prompt)
            if not response.strip():
                raise RuntimeError('Empty response')
            print('PASS: live local Ollama generated a draft')
            print('Draft preview (FICTIONAL TEST DATA):')
            print(response[:1600])
        except Exception as exc:
            print(f'FAIL: live Ollama: {type(exc).__name__}: {exc}')
            return 1
    print('No CRM data modified. No messages sent.')
    return 0

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true',help='also call local Ollama')
    args=parser.parse_args()
    sys.exit(run(args.live))
