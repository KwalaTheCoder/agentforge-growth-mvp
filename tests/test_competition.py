import unittest
from unittest.mock import patch
import paid_opportunity_radar as r

class CompetitionTests(unittest.TestCase):
    def test_missing_api_not_zero(self):
        with patch.object(r, '_github_get', return_value=(None, 'rate limited')):
            c = r._competition_check({'url':'https://github.com/a/b/issues/3'}, {}, 3)
        self.assertEqual(c['state'], 'unknown')
        self.assertIsNone(c['linked_pr_count'])
    def test_detect_pr(self):
        issue = {'state':'open','assignees':[]}
        timeline = [{'source':{'issue':{'pull_request':{},'html_url':'https://github.com/a/b/pull/4'}}}]
        with patch.object(r, '_github_get', side_effect=[(issue,None),(timeline,None),([],None)]):
            c=r._competition_check({'url':'https://github.com/a/b/issues/3'}, {}, 3)
        self.assertEqual(c['state'],'competition_detected')
        self.assertEqual(c['linked_pr_count'],1)
    def test_assigned_blocks(self):
        with patch.object(r, '_github_get', side_effect=[({'state':'open','assignee':{'login':'a'}},None),([],None),([],None)]):
            c=r._competition_check({'url':'https://github.com/a/b/issues/3'}, {}, 3)
        self.assertEqual(c['state'],'blocked')
    def test_evaluate_compat(self):
        item=r.evaluate({'title':'Add API integration bounty $3 USDC','body':'Task: integrate API. Reward $3 USDC','state':'open','labels':[],'updated_at':'2026-10-22T00:00:00Z','html_url':'https://github.com/a/b/issues/3'})
        self.assertIn('competition',item)
        self.assertFalse(item['outreach_approved'])

if __name__=='__main__': unittest.main()
