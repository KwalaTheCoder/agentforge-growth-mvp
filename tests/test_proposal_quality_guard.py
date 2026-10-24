import unittest
from proposal_quality_guard import review_proposal, generate_reviewed_draft
class ProposalGuardTests(unittest.TestCase):
    def test_reversed_role(self):
        d="Dear developer, We are seeking your expertise in Python development. Please submit your application to our team."
        self.assertTrue(review_proposal(d)['needs_revision'])
    def test_valid_direction(self):
        d="Subject: API support\\nHello, our team can help with your documented API integration. We can discuss the scope and suggest a technical approach. Would a short discussion about authentication and error handling be useful? Regards, Engineering Team"
        self.assertFalse(review_proposal(d)['needs_revision'])
    def test_retry(self):
        calls=[]
        def gen(prompt):
            calls.append(prompt)
            return ("We are seeking a developer. Please submit your application to our team." if len(calls)==1 else "Hello, our team can help with API integrations. We can discuss requirements and technical constraints, and provide a scoped proposal after reviewing the documented issue. Regards, Engineering Team.")
        result=generate_reviewed_draft(gen,"Prompt")
        self.assertEqual(result['attempts'],2)
        self.assertFalse(result['review']['needs_revision'])
    def test_still_bad(self):
        result=generate_reviewed_draft(lambda p:"We are seeking a developer. Please submit your application.",'prompt')
        self.assertTrue(result['review']['needs_revision'])
        self.assertEqual(result['attempts'],2)
