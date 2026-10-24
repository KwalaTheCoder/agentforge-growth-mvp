import unittest
from opportunity_decision import decide

class DecisionTests(unittest.TestCase):
    def test_peera(self):
        rows = [
            {'title':'Feature requests','v49_priority':15,'age_days':2454,'current_state':'open','rechecked':True},
            {'title':'Community link bug','v49_priority':15,'age_days':2138,'current_state':'open','rechecked':True},
            {'title':'test issue name','v49_priority':0,'age_days':1126,'current_state':'open','rechecked':True},
        ]
        result=decide({'company':'Peera AI','items':rows})
        self.assertEqual(result['counts'], {'Investigate':0,'Monitor':0,'Archive':3})
        self.assertFalse(result['crm_modified'])
    def test_recent_explicit_candidate(self):
        row={'title':'Paid bounty','v49_priority':90,'age_days':3,'current_state':'open','rechecked':True,'payment_wording_found':True}
        result=decide({'items':[row]})
        self.assertEqual(result['counts']['Investigate'],1)
        self.assertFalse(result['outreach_authorized'])
    def test_recent_without_request_is_monitor(self):
        row={'title':'Fix API','v49_priority':65,'age_days':2,'current_state':'open','rechecked':True}
        self.assertEqual(decide({'items':[row]})['items'][0]['decision'],'Monitor')
    def test_unchecked_is_monitor(self):
        row={'title':'Paid bounty','v49_priority':80,'age_days':1,'current_state':'Not rechecked','rechecked':False,'payment_wording_found':True}
        self.assertEqual(decide({'items':[row]})['items'][0]['decision'],'Monitor')
    def test_closed_is_archive(self):
        row={'title':'Paid bounty','v49_priority':10,'age_days':1,'current_state':'closed','rechecked':True,'payment_wording_found':True}
        self.assertEqual(decide({'items':[row]})['items'][0]['decision'],'Archive')

if __name__ == '__main__': unittest.main()
