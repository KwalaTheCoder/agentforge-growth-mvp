import unittest
from datetime import date
from lead_prioritization import prioritize,ranked
BASE={'company':'Example','source_url':'https://github.com/example','service':'Python / Backend',
      'stage':'Research','identity_checked':0,'need_checked':0,'contact_permission_checked':0}
class LeadPriorityTests(unittest.TestCase):
    def test_technical_only_not_buyer(self):
        x=prioritize(BASE,date(2026,10,21))
        self.assertFalse(x['outreach_ready'])
        self.assertEqual(x['research_score'],20)
    def test_followup_due_not_authorization(self):
        x=prioritize(dict(BASE,followup='2026-10-20'),date(2026,10,21))
        self.assertTrue(x['followup_due'])
        self.assertFalse(x['outreach_ready'])
    def test_terminal_not_actionable(self):
        x=prioritize(dict(BASE,stage='Won',followup='2026-10-20'),date(2026,10,21))
        self.assertEqual(x['research_score'],0)
        self.assertFalse(x['followup_due'])
    def test_qualified_requires_all_gates(self):
        x=prioritize(dict(BASE,identity_checked=1,need_checked=1,
                          need_evidence='Documented request',evidence_url='https://example.org/request',
                          contact_channel='Public business form',contact_permission_checked=1),date(2026,10,21))
        self.assertTrue(x['outreach_ready'])
        self.assertLessEqual(x['research_score'],100)
    def test_invalid_date_not_due(self):
        x=prioritize(dict(BASE,followup='not-a-date'),date(2026,10,21))
        self.assertFalse(x['followup_due'])
    def test_rank_due_first(self):
        a=dict(BASE,company='A',followup='2026-10-20')
        b=dict(BASE,company='B',identity_checked=1)
        self.assertEqual(ranked([b,a],date(2026,10,21))[0]['company'],'A')
    def test_no_mutation(self):
        r=dict(BASE);prioritize(r,date(2026,10,21));self.assertEqual(r,BASE)
