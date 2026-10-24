import unittest
from lead_qualification import assess_lead, draft_prompt

GOOD={'company':'Sample Co','source_url':'https://github.com/sample','service':'Python / Backend',
'need_evidence':'Public request for an external backend contractor',
'evidence_url':'https://example.org/request','contact_channel':'Public business inquiry form',
'identity_checked':True,'need_checked':True,'contact_permission_checked':True}
class QualificationTests(unittest.TestCase):
    def test_ready_does_not_auto_authorize(self):
        r=assess_lead(GOOD)
        self.assertEqual(r['status'],'Ready for human outreach review')
        self.assertFalse(r['outreach_authorized_automatically'])
        self.assertTrue(r['manual_review_required'])
    def test_missing_need(self):
        r=assess_lead({**GOOD,'need_evidence':''})
        self.assertEqual(r['recommended_stage'],'Research')
        with self.assertRaises(ValueError):draft_prompt({**GOOD,'need_evidence':''})
    def test_unverified_channel(self):
        self.assertEqual(assess_lead({**GOOD,'contact_permission_checked':False})['recommended_stage'],'Research')
    def test_bad_url(self):
        self.assertEqual(assess_lead({**GOOD,'evidence_url':'javascript:alert(1)'})['recommended_stage'],'Research')
    def test_draft_uses_evidence(self):
        s=draft_prompt(GOOD)
        self.assertIn('Public request for an external backend contractor',s)
        self.assertIn('never send it',s)
if __name__=='__main__': unittest.main()
