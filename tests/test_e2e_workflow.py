"""Stage 16 integration tests. Never access real DB, GitHub, or Ollama."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import direct_b2b
from lead_qualification import assess_lead, draft_prompt
from direct_client_discovery import organization_research

BASE={'company':'Example Lab','source_url':'https://github.com/example-lab',
      'website':'','country':'Germany','description':'Public technical company',
      'service':'Python / Backend','need_evidence':'','evidence_url':'',
      'contact_channel':'','contact_permission_checked':False,'identity_checked':False,
      'need_checked':False,'stage':'Research','notes':'','draft':'','followup':''}
READY={**BASE,'need_evidence':'Public request explicitly asks for external API development',
       'evidence_url':'https://example.org/public-request',
       'contact_channel':'Verified business contact form',
       'contact_permission_checked':True,'identity_checked':True,'need_checked':True}
class E2EWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patch=patch.object(direct_b2b,'DB',Path(self.tmp.name)/'isolated.sqlite3')
        self.patch.start()
    def tearDown(self):
        self.patch.stop();self.tmp.cleanup()
    def test_research_save_restart_readback_and_no_duplicate(self):
        direct_b2b.save(BASE)
        self.assertEqual(direct_b2b.all_prospects()[0]['stage'],'Research')
        direct_b2b.save({**BASE,'notes':'second revision'})
        rows=direct_b2b.all_prospects()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['notes'],'second revision')
        self.assertEqual(assess_lead(rows[0])['recommended_stage'],'Research')
        with self.assertRaises(ValueError):draft_prompt(rows[0])
    def test_cannot_bypass_gate_by_saving_qualified(self):
        with self.assertRaises(ValueError):direct_b2b.save({**BASE,'stage':'Qualified'})
        self.assertEqual(direct_b2b.all_prospects(),[])
    def test_qualified_manual_path_and_draft(self):
        direct_b2b.save({**READY,'stage':'Qualified'})
        row=direct_b2b.all_prospects()[0]
        self.assertEqual(assess_lead(row)['recommended_stage'],'Qualified')
        text=draft_prompt(row)
        self.assertIn('external API development',text)
        self.assertIn('never send it',text)
    def test_no_automatic_contact_stage(self):
        with self.assertRaises(ValueError):direct_b2b.save({**READY,'stage':'Contacted'})
    @patch('direct_client_discovery.CLIENT.get')
    def test_public_research_never_proves_buyer_intent(self,get):
        get.side_effect=[{'type':'Organization','name':'Example Lab'},
                         {'items':[{'title':'Webhook bug','body':'API 403',
                                    'html_url':'https://github.com/example-lab/api/issues/3'}]}]
        result=organization_research('example-lab')
        self.assertFalse(result['buyer_need_verified'])
        self.assertEqual(result['qualification'],'Research Only')
    @patch('direct_b2b.requests.post')
    def test_ollama_draft_success_and_failure(self,post):
        post.return_value=Mock(status_code=200,json=lambda:{'response':'Draft for manual review'})
        self.assertEqual(direct_b2b.ollama_generate(draft_prompt(READY)),'Draft for manual review')
        post.side_effect=ConnectionError('Ollama offline')
        with self.assertRaises(ConnectionError):direct_b2b.ollama_generate(draft_prompt(READY))
    def test_invalid_evidence_does_not_qualify(self):
        with self.assertRaises(ValueError):direct_b2b.save({**READY,'evidence_url':'javascript:alert(1)','stage':'Qualified'})
    def test_research_cannot_generate_draft(self):
        for field in ('identity_checked','need_checked','contact_permission_checked','contact_channel','evidence_url'):
            candidate={**READY,field:False if field.endswith('checked') else ''}
            self.assertNotEqual(assess_lead(candidate)['recommended_stage'],'Qualified')
            with self.assertRaises(ValueError):draft_prompt(candidate)
