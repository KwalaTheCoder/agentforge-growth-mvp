import json
import unittest
from full_company_research import collect_company_research, synthesis_prompt, generate_full_report, export_report

class FullCompanyResearchTests(unittest.TestCase):
    def setUp(self):
        self.record = {'company':'Example','source_url':'https://github.com/example','website':'https://example.org'}

    def test_both_sources(self):
        r=collect_company_research(self.record, lambda _: {'profile':{'company':'Example'},'issues':[]},
                                   lambda _: {'source_url':'https://example.org','public_page_excerpt':'Hello'})
        self.assertIsNotNone(r['github']);self.assertIsNotNone(r['website'])
        self.assertFalse(r['commercial_need_verified']);self.assertFalse(r['messages_sent'])

    def test_one_source_failure_preserved(self):
        def fail(_): raise RuntimeError('network unavailable')
        r=collect_company_research(self.record, fail, lambda _: {'source_url':'https://example.org'})
        self.assertIn('network unavailable',r['errors']['github'])
        self.assertIsNotNone(r['website'])

    def test_no_evidence_disables_ai(self):
        with self.assertRaises(ValueError): generate_full_report({'github':None,'website':None})

    def test_prompt_not_buyer_proof(self):
        p=synthesis_prompt({'company':'X','github':{'profile':{},'issues':[{'title':'paid bounty','url':'https://github.com/x/y/issues/1'}]},'website':None})
        self.assertIn('Research Only',p)
        self.assertIn('untrusted',p.lower())

    def test_export(self):
        r=json.loads(export_report({'company':'Example'},'draft'))
        self.assertFalse(r['outreach_authorized'])
        self.assertIn('Research Only',r['qualification'])

    def test_missing_company(self):
        with self.assertRaises(ValueError): collect_company_research({})

if __name__=='__main__': unittest.main()
