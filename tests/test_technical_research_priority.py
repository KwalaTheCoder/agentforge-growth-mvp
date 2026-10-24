import unittest
from technical_research_priority import prioritize

class PriorityTests(unittest.TestCase):
    def row(self,title,age,state='open',checked=True):
        return {'title':title,'age_days':age,'current_state':state,'rechecked':checked,'url':title}
    def test_fresh_vs_old(self):
        x=prioritize({'items':[self.row('Failure corrupts model data during inference',1),self.row('Failure corrupts model data during inference',83)]})
        self.assertGreater(x['items'][0]['technical_research_score'],x['items'][1]['technical_research_score'])
    def test_placeholder_zero(self):
        self.assertEqual(prioritize({'items':[self.row('test issue name',1)]})['items'][0]['technical_research_score'],0)
    def test_closed_capped(self):
        self.assertLessEqual(prioritize({'items':[self.row('Crash corrupt data during inference',1,'closed')]})['items'][0]['technical_research_score'],20)
    def test_missing_age_capped(self):
        self.assertLessEqual(prioritize({'items':[self.row('Crash corrupt data during inference',None)]})['items'][0]['technical_research_score'],20)
    def test_no_commercial_inference(self):
        x=prioritize({'items':[self.row('Crash corrupt data during inference',1)]})
        self.assertFalse(x['commercial_need_verified']);self.assertFalse(x['outreach_authorized']);self.assertFalse(x['crm_modified'])
    def test_sort(self):
        x=prioritize({'items':[self.row('Feature requests',83),self.row('Crash corrupt data during inference',1)]})
        self.assertEqual(x['items'][0]['age_days'],1)
if __name__=='__main__':unittest.main()
