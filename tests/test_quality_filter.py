import unittest
from opportunity_discovery import rank_issue, assess_work_availability

class QualityTests(unittest.TestCase):
    def test_existing_contributor_payout(self):
        issue={'title':'Bounty Proposal: Reusable Deploy Ancestry Guard & CI Pipeline Hardening ($100 - $125 USD)',
            'body':'Pull Request: #21192\nImplements an end-to-end reusable ancestry guard.\n14/14 unit tests passing.\nDesignated Payout Rail: USDC wallet',
            'state':'open'}
        row=rank_issue(issue)
        self.assertEqual(row['work_availability'],'Already Implemented / Claimed')
        self.assertEqual(row['priority_score'],0)
        self.assertFalse(row['commercially_verified'])
    def test_open_invitation(self):
        result=assess_work_availability({'title':'Paid backend task', 'body':'Looking for a Python developer to implement the API.', 'state':'open'})
        self.assertEqual(result['work_availability'],'Open for Applicants')
    def test_ambiguous_bounty(self):
        result=assess_work_availability({'title':'$200 bounty', 'body':'Please fix this bug', 'state':'open'})
        self.assertEqual(result['work_availability'],'Unknown — Manual Review')
    def test_closed_issue(self):
        result=assess_work_availability({'title':'Fix backend', 'body':'Open for applicants', 'state':'closed'})
        self.assertEqual(result['work_availability'],'Already Implemented / Claimed')
    def test_proposal(self):
        result=assess_work_availability({'title':'Bounty Proposal: CI work', 'body':'Proposed solution', 'state':'open'})
        self.assertEqual(result['work_availability'],'Proposal Awaiting Maintainer Approval')
if __name__=='__main__': unittest.main()
