import unittest
from datetime import datetime, timezone
from evidence_quality import age_days, issue_locator, grade_issue, assess_evidence

NOW = datetime(2026, 10, 22, tzinfo=timezone.utc)
URL = 'https://github.com/ambianic/fall-detection/issues/36'
ISSUE = {'title':'Fall detection', 'url':URL, 'updated_at':'2021-10-11T16:06:49Z', 'funding_signal':'No Payment Evidence'}

class Tests(unittest.TestCase):
    def test_old_evidence(self):
        row=grade_issue(ISSUE, {'state':'open', 'updated_at':ISSUE['updated_at']}, NOW)
        self.assertEqual(row['freshness'], 'Stale (>2 years)')
        self.assertFalse(row['commercial_need_verified'])
    def test_closed_has_low_priority(self):
        row=grade_issue(ISSUE, {'state':'closed', 'updated_at':'2026-10-21T00:00:00Z'}, NOW)
        self.assertLessEqual(row['research_priority'], 10)
    def test_recent_open(self):
        row=grade_issue(ISSUE, {'state':'open', 'updated_at':'2026-10-21T00:00:00Z'}, NOW)
        self.assertGreater(row['research_priority'], 50)
    def test_reject_foreign_issue(self):
        with self.assertRaises(ValueError):
            issue_locator('https://github.com/other/repo/issues/1', 'ambianic')
    def test_no_recheck_does_not_claim_open(self):
        report={'company':'Ambianic.ai','github':{'organization':'ambianic','issues':[ISSUE]}}
        result=assess_evidence(report, recheck=False, now=NOW)
        self.assertEqual(result['issues'][0]['current_state'], 'Not rechecked')
        self.assertFalse(result['commercial_need_verified'])
    def test_recheck(self):
        class Response:
            status_code=200
            def raise_for_status(self): pass
            def json(self): return {'state':'closed', 'updated_at':'2026-10-21T00:00:00Z'}
        report={'company':'Ambianic.ai','github':{'organization':'ambianic','issues':[ISSUE]}}
        result=assess_evidence(report, now=NOW, fetch=lambda *a,**kw:Response())
        self.assertEqual(result['rechecked_count'],1)
        self.assertEqual(result['issues'][0]['current_state'],'closed')
        self.assertFalse(result['crm_modified'])

if __name__=='__main__': unittest.main()
