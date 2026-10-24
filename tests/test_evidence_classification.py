import unittest
from direct_b2b import classify_public_issue

class EvidenceClassificationTests(unittest.TestCase):
    def test_epilot_webhook_bug_is_signal(self):
        issue = {'title': '[svc-webhooks] 403 error when creating webhook with environment variables directly',
                 'excerpt': 'This is a backend bug in svc-webhooks. Fix needs to be applied in backend service.'}
        result = classify_public_issue(issue)
        self.assertEqual(result['category'], 'Technical Signal')
        self.assertFalse(result['commercially_verified'])

    def test_contribution_not_paid(self):
        result = classify_public_issue({'title': 'Help wanted: improve docs', 'excerpt': 'Contributions welcome.'})
        self.assertEqual(result['category'], 'External Contribution Requested')
        self.assertFalse(result['commercially_verified'])

    def test_paid_candidate_not_verified(self):
        result = classify_public_issue({'title': 'Paid bounty: fix API', 'excerpt': 'We will pay for this fix.'})
        self.assertEqual(result['category'], 'Paid Opportunity Candidate')
        self.assertFalse(result['commercially_verified'])

    def test_budget_word_alone_is_not_paid(self):
        result = classify_public_issue({'title': 'budget allocation bug', 'excerpt': 'No payment details.'})
        self.assertEqual(result['category'], 'Technical Signal')

if __name__ == '__main__':
    unittest.main()
