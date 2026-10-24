import unittest
from datetime import date
from growth_operations import summarize, rows
class GrowthOperationsTests(unittest.TestCase):
    def setUp(self):
        self.data=[
            {'company':'A','stage':'Research','followup':'2026-10-19','notes':'secret'},
            {'company':'B','stage':'Draft ready','draft':'Draft text','followup':'2026-10-21'},
            {'company':'C','stage':'Won','followup':'2026-10-01'},
            {'company':'D','stage':'Qualified','followup':'bad'},
            {'company':'E','stage':'Draft ready','draft':'  '},
        ]
    def test_total_and_stages(self):
        r=summarize(self.data,date(2026,10,21))
        self.assertEqual(r['total'],5)
        self.assertEqual(r['stages']['Draft ready'],2)
    def test_due_excludes_closed(self):
        r=summarize(self.data,date(2026,10,21))
        self.assertEqual({x['company'] for x in r['due']},{'A','B'})
        self.assertEqual([x['company'] for x in r['overdue']],['A'])
    def test_draft_requires_saved_text(self):
        self.assertEqual([x['company'] for x in summarize(self.data,date(2026,10,21))['drafts_for_review']],['B'])
    def test_invalid_dates(self):
        self.assertEqual(len(summarize(self.data,date(2026,10,21))['invalid_dates']),1)
    def test_does_not_mutate(self):
        before=repr(self.data)
        summarize(self.data,date(2026,10,21))
        self.assertEqual(repr(self.data),before)
    def test_whitelisted_fields(self):
        self.assertNotIn('notes',rows(self.data)[0])
        self.assertNotIn('draft',rows(self.data)[1])
    def test_empty(self):
        self.assertEqual(summarize([],date(2026,10,21))['total'],0)
