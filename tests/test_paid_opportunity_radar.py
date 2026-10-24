import sys,unittest
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from paid_opportunity_radar import evaluate
NOW=datetime(2026,10,22,tzinfo=timezone.utc)
BASE={'title':'Paid bounty: Python API integration $400','body':'Implement FastAPI endpoint with tests','state':'open','updated_at':'2026-10-21T00:00:00Z','labels':[{'name':'bounty'}],'html_url':'https://github.com/a/b/issues/1'}
class TestRadar(unittest.TestCase):
 def test_skill_and_payment(self):
  r=evaluate(BASE,NOW); self.assertIn('Python',r['skill_matches']); self.assertTrue(r['amount_mentions_unverified']); self.assertGreater(r['score'],30)
 def test_archived_duplicate(self):
  r=evaluate(dict(BASE,body='Archived duplicate. Not a current invitation.'),NOW); self.assertLessEqual(r['score'],35); self.assertNotEqual(r['status'],'Review manually')
 def test_stale(self):
  r=evaluate(dict(BASE,updated_at='2020-01-01T00:00:00Z'),NOW); self.assertIn('not updated in 180+ days',r['red_flags'])
 def test_unpaid(self):
  r=evaluate(dict(BASE,title='Python API integration',body='Fix an endpoint'),NOW); self.assertIn('no explicit monetary evidence',r['red_flags'])
 def test_assigned(self):
  r=evaluate(dict(BASE,assignee={'login':'somebody'}),NOW); self.assertIn('assigned; check availability',r['red_flags'])
if __name__=='__main__':unittest.main()
