import unittest
from evidence_relevance import prioritize

class RelevanceTests(unittest.TestCase):
    def setUp(self):
        self.quality = {'company':'Peera AI', 'issues':[
            {'title':'test issue name','url':'https://github.com/a/b/issues/1','age_days':1126,'current_state':'open','rechecked':True,'research_priority':35},
            {'title':'Community link refreshing','url':'https://github.com/a/b/issues/2','age_days':2138,'current_state':'open','rechecked':True,'research_priority':35},
            {'title':'Paid bounty: $300 for API fix','url':'https://github.com/a/b/issues/3','age_days':5,'current_state':'open','rechecked':True,'research_priority':75},
        ]}
    def test_test_issue_is_zero(self):
        result=prioritize(self.quality)
        self.assertEqual(next(x for x in result['items'] if 'test issue' in x['title'])['v49_priority'],0)
    def test_stale_deprioritized(self):
        result=prioritize(self.quality)
        self.assertLessEqual(next(x for x in result['items'] if 'Community' in x['title'])['v49_priority'],15)
    def test_paid_wording_not_verified(self):
        result=prioritize(self.quality)
        item=result['review_first'][0]
        self.assertTrue(item['payment_wording_found'])
        self.assertFalse(item['commercial_need_verified'])
    def test_no_outreach_or_crm(self):
        result=prioritize(self.quality)
        self.assertFalse(result['messages_sent'])
        self.assertFalse(result['crm_modified'])
    def test_closed_not_prioritized(self):
        q={'issues':[{'title':'Paid bounty $300','age_days':1,'current_state':'closed','rechecked':True,'research_priority':10}]}
        self.assertEqual(prioritize(q)['review_first'],[])
    def test_missing_date_not_prioritized(self):
        q={'issues':[{'title':'Feature request','age_days':None,'current_state':'open','rechecked':True,'research_priority':35}]}
        self.assertEqual(prioritize(q)['review_first'],[])
if __name__=='__main__': unittest.main()
