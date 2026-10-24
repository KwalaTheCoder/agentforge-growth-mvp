import unittest
from unittest.mock import patch
from opportunity_discovery import rank_issue, discover_opportunities, parse_issue_url

class DiscoveryTests(unittest.TestCase):
    def test_unfunded_bounty(self):
        row=rank_issue({'title':'[0.10 USDC autonomous bounty] Complete earning loop',
                        'body':'Current status: not funded yet. Planned funding: 0.11 USDC',
                        'state':'open','url':'https://github.com/NSPG13/agent-bounties/issues/297'})
        self.assertEqual(row['classification'],'Paid Opportunity Candidate')
        self.assertEqual(row['funding_status'],'Unfunded')
        self.assertFalse(row['commercially_verified'])

    def test_epilot_technical(self):
        row=rank_issue({'title':'403 error creating webhook','body':'POST fails with env variables',
                        'state':'open'})
        self.assertEqual(row['classification'],'Technical Signal')
        self.assertEqual(row['funding_status'],'No Payment Evidence')

    def test_reject_non_github_url(self):
        with self.assertRaises(ValueError):
            parse_issue_url('https://evil.example/owner/repo/issues/1')

    @patch('opportunity_discovery.inspect_issue')
    @patch('opportunity_discovery._request')
    def test_discovery_dedupes_and_skips_pr(self, get, inspect):
        get.return_value={'items':[{'html_url':'https://github.com/a/b/issues/1'},
                                  {'html_url':'https://github.com/a/b/issues/1'},
                                  {'html_url':'https://github.com/a/b/issues/2','pull_request':{}}],
                          'incomplete_results':False}
        inspect.return_value={'title':'Bug','body':'Fix this','state':'open'}
        result=discover_opportunities('Bounty',10)
        self.assertEqual(len(result['items']),1)
        inspect.assert_called_once()
if __name__=='__main__':
    unittest.main()
