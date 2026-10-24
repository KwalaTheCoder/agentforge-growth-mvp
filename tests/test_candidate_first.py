import unittest
from unittest.mock import patch
from opportunity_discovery import assess_actionability, discover_opportunities

class CandidateFirstTests(unittest.TestCase):
    def test_existing_payout_excluded(self):
        row={'work_availability':'Already Implemented / Claimed','funding_status':'Funding Unverified','classification':'Paid Opportunity Candidate'}
        self.assertEqual(assess_actionability(row)[0],'Excluded')
    def test_unfunded_research_only(self):
        row={'work_availability':'Open for Applicants','funding_status':'Unfunded','classification':'Paid Opportunity Candidate'}
        self.assertEqual(assess_actionability(row)[0],'Research Only')
    def test_explicit_invitation_review_first(self):
        row={'work_availability':'Open for Applicants','funding_status':'Funding Unverified','classification':'Paid Opportunity Candidate'}
        self.assertEqual(assess_actionability(row)[0],'Review First')
    @patch('opportunity_discovery.inspect_issue')
    @patch('opportunity_discovery._request')
    def test_three_queries_dedupe(self, request, inspect):
        request.return_value={'items':[{'html_url':'https://github.com/o/r/issues/1','title':'Paid bounty $200','updated_at':'2026-10-20'}], 'incomplete_results':False}
        inspect.return_value={'title':'Paid bounty $200','body':'Looking for a Python developer to implement the API. Payment offered $200.', 'state':'open','url':'https://github.com/o/r/issues/1','updated_at':'2026-10-20'}
        result=discover_opportunities('Bounty',20)
        self.assertEqual(request.call_count,3)
        inspect.assert_called_once()
        self.assertEqual(result['unique_search_hits'],1)
        self.assertEqual(result['items'][0]['actionability'],'Review First')
if __name__=='__main__':unittest.main()
