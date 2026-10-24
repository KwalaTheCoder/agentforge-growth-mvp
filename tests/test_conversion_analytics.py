import unittest
from conversion_analytics import snapshot, safe_rows, STAGES

class ConversionAnalyticsTests(unittest.TestCase):
    def test_empty(self):
        r=snapshot([])
        self.assertEqual(r['total'],0)
        self.assertIsNone(r['current_won_share_pct'])
        self.assertIsNone(r['historical_conversion_rates'])
    def test_research_only(self):
        r=snapshot([{'source_url':'https://github.com/epilot-dev','stage':'Research'}])
        self.assertEqual(r['active'],1)
        self.assertEqual(r['won'],0)
        self.assertEqual(r['current_won_share_pct'],0)
    def test_counts(self):
        r=snapshot([{'source_url':f'https://example.com/{i}','stage':s} for i,s in enumerate(STAGES)])
        self.assertEqual(r['total'],8)
        self.assertEqual(r['active'],6)
        self.assertEqual(r['terminal'],2)
        self.assertEqual(r['current_won_share_pct'],12.5)
    def test_dedup_latest(self):
        r=snapshot([{'source_url':'https://example.com/a','stage':'Research','updated_at':'2026-01-01'},
                    {'source_url':'https://example.com/a','stage':'Qualified','updated_at':'2026-02-01'}])
        self.assertEqual(r['total'],1)
        self.assertEqual(r['stages']['Qualified'],1)
        self.assertEqual(r['duplicate_rows_removed'],1)
    def test_unknown(self):
        r=snapshot([{'source_url':'https://example.com/a','stage':'Other'}])
        self.assertEqual(r['unknown_stages']['Other'],1)
    def test_missing_source(self):
        r=snapshot([{'company':'No source'}])
        self.assertEqual(r['missing_source_count'],1)
        self.assertEqual(r['total'],0)
    def test_safe_rows(self):
        rows=safe_rows([{'company':'Example','stage':'Research','source_url':'https://example.com',
                         'notes':'PRIVATE','draft':'SECRET','contact_channel':'email'}])
        self.assertNotIn('PRIVATE',str(rows))
        self.assertNotIn('SECRET',str(rows))
        self.assertNotIn('email',str(rows))
    def test_no_false_conversion(self):
        r=snapshot([{'source_url':'https://example.com/a','stage':'Won'}])
        self.assertFalse(r['history_available'])
        self.assertIsNone(r['historical_conversion_rates'])
