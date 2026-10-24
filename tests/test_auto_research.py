import unittest
from unittest.mock import patch
from auto_research import github_org_login, research_company, evidence_memo

class AutoResearchTests(unittest.TestCase):
    def test_reject_non_github(self):
        for url in ('http://github.com/abc', 'https://evil.test/abc', 'https://github.com/abc/repo', 'https://github.com@evil.test/abc'):
            with self.assertRaises(ValueError): github_org_login(url)
    def test_accept_org(self):
        self.assertEqual(github_org_login('https://github.com/IterateAI'), 'IterateAI')
    @patch('auto_research.discover_public_issue_signals')
    @patch('auto_research.github_profile')
    def test_readonly_report(self, profile, signals):
        profile.return_value={'source_url':'https://github.com/IterateAI','company':'IterateAI','website':'https://iterate.ai','description':'AI'}
        signals.return_value={'issues':[{'title':'Bug','url':'https://github.com/IterateAI/a/issues/1','repository':'IterateAI/a','updated_at':'2026-01-01','excerpt':'bug'}], 'incomplete_results':False}
        r=research_company('https://github.com/IterateAI')
        self.assertFalse(r['commercial_need_verified'])
        self.assertFalse(r['contact_permission_verified'])
        self.assertIn('NOT VERIFIED', evidence_memo(r))
        self.assertEqual(len(r['issues']),1)

if __name__=='__main__': unittest.main()
