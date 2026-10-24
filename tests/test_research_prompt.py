import unittest
from direct_b2b import research_prompt

class ResearchPromptTests(unittest.TestCase):
    def test_requires_company_and_source(self):
        with self.assertRaises(ValueError):
            research_prompt({'company': 'epilot'})
    def test_marks_hypotheses_unverified(self):
        result=research_prompt({'company':'epilot','source_url':'https://github.com/epilot-dev','description':'Energy SaaS'})
        self.assertIn('unverified',result)
        self.assertIn('not an outreach message',result)
        self.assertIn('Energy SaaS',result)
    def test_rejects_bad_url(self):
        with self.assertRaises(ValueError):
            research_prompt({'company':'X','source_url':'file:///etc/passwd'})

if __name__=='__main__':
    unittest.main()
