import unittest
from opportunity_intelligence import analyze_issue
from opportunity_discovery import rank_issue,assess_actionability

class IntelligenceTests(unittest.TestCase):
 def test_delivered_proposal(self):
  i={'title':'Bounty Proposal: CI Pipeline ($100 - $125 USD)','body':'Implements the solution. Pull Request: #21192. Designated Payout Rail: USDC','state':'open'}
  self.assertEqual(analyze_issue(i)['intelligence_label'],'Not an Opportunity')
  self.assertEqual(assess_actionability(rank_issue(i))[0],'Excluded')
 def test_unfunded(self):
  i={'title':'0.10 USDC bounty','body':'Open for applicants. Current status: not funded yet. 0.10 USDC solver reward','state':'open'}
  self.assertEqual(analyze_issue(i)['intelligence_label'],'Research Candidate')
 def test_technical_issue(self):
  i={'title':'403 webhook error','body':'backend POST request fails','state':'open'}
  self.assertEqual(analyze_issue(i)['intelligence_label'],'Not an Opportunity')
 def test_open_paid_invitation(self):
  i={'title':'Paid bounty $250','body':'Open for applicants. Reward $250 for developer to implement Python API.','state':'open'}
  self.assertEqual(analyze_issue(i)['intelligence_label'],'Actionable Opportunity')
  self.assertFalse(analyze_issue(i)['commercially_verified'])
 def test_bounty_without_invitation(self):
  i={'title':'Bounty $200','body':'Maybe we should fund this in the future','state':'open'}
  self.assertEqual(analyze_issue(i)['intelligence_label'],'Research Candidate')
 def test_closed(self):
  self.assertEqual(analyze_issue({'title':'Paid $500','body':'Open for applicants','state':'closed'})['intelligence_label'],'Not an Opportunity')
if __name__=='__main__': unittest.main()
