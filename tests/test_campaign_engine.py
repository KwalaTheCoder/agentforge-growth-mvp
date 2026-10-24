import unittest
from campaign_engine import normalize_orgs,run_campaign,proposal_prompt
class TestCampaign(unittest.TestCase):
 def test_normalize(self):self.assertEqual(normalize_orgs('ai2cm\nai2cm\npeeranha'),['ai2cm','peeranha'])
 def test_reject(self):
  with self.assertRaises(ValueError):normalize_orgs('https://evil.example/path')
 def test_isolate_failure(self):
  def runner(org):
   if org=='bad':raise RuntimeError('offline')
   return {'company':org,'top_score':55,'issues_found':2}
  report=run_campaign(['bad','good'],runner=runner)
  self.assertEqual(report['results'][0]['company'],'good')
  self.assertFalse(report['messages_sent'])
 def test_no_unsourced_proposal(self):
  with self.assertRaises(ValueError):proposal_prompt({'company':'X','top_evidence':[]},'Python')
 def test_prompt_no_permission(self):
  s=proposal_prompt({'company':'X','source_url':'https://github.com/x','top_evidence':[{'url':'https://github.com/x/y/issues/1','title':'Bug'}]},'Python')
  self.assertIn('Do not claim a purchase request',s)
if __name__=='__main__':unittest.main()
