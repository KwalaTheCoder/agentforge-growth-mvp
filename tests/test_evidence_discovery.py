import unittest
from unittest.mock import patch
import direct_b2b

class FakeResponse:
    status_code = 200
    def raise_for_status(self): pass
    def json(self):
        return {'items': [
            {'html_url':'https://github.com/epilot-dev/sample/issues/4','title':'Fix API','body':'Internal bug', 'labels':[], 'updated_at':'2026-10-01'},
            {'html_url':'https://github.com/other/sample/issues/5','title':'Other org'},
            {'html_url':'https://github.com/epilot-dev/sample/pull/6','title':'PR', 'pull_request':{}},
        ], 'incomplete_results': False}

class EvidenceTests(unittest.TestCase):
    @patch('direct_b2b.requests.get', return_value=FakeResponse())
    def test_public_issue_is_not_buyer_evidence(self, get):
        result=direct_b2b.discover_public_issue_signals('https://github.com/epilot-dev')
        self.assertEqual(len(result['issues']),1)
        self.assertIn('NOT verified',result['issues'][0]['classification'])
        self.assertEqual(get.call_args.kwargs['params']['q'],'org:epilot-dev is:issue is:open')
    def test_reject_non_org_url(self):
        with self.assertRaises(ValueError):
            direct_b2b.discover_public_issue_signals('https://github.com/epilot-dev/repo')
    def test_reject_other_hosts(self):
        with self.assertRaises(ValueError):
            direct_b2b.discover_public_issue_signals('https://example.com/epilot-dev')

if __name__ == '__main__': unittest.main()
