import unittest
from unittest.mock import patch
import paid_opportunity_radar as radar

class RadarTests(unittest.TestCase):
    def issue(self, **kwargs):
        d=dict(title='[PAID BOUNTY $90] Implement Python API', body='Implement endpoint. Reward: $90 USD', state='open', updated_at='2026-10-23T00:00:00Z', labels=[], html_url='https://github.com/example/repo/issues/1')
        d.update(kwargs)
        return d
    def test_normal(self):
        self.assertEqual(radar.evaluate(self.issue())['status'], 'Review manually')
    def test_mirror(self):
        i=self.issue(body='Implement endpoint. Reward: $90 USD\nSource URL: https://github.com/real/repo/issues/11')
        r=radar.evaluate(i)
        self.assertEqual(r['original_url'], 'https://github.com/real/repo/issues/11')
        self.assertEqual(r['status'], 'Hold / verify')
    def test_404_never_actionable(self):
        item=radar.evaluate(self.issue())
        with patch.object(radar, '_github_get', return_value=(None, '404 Not Found')):
            radar._validate_candidate(item, {}, 1)
        self.assertEqual(item['status'], 'Skip')
        self.assertEqual(item['verification']['state'], 'blocked')
    def test_closed_is_skip(self):
        item=radar.evaluate(self.issue())
        with patch.object(radar, '_github_get', return_value=({'state':'closed','assignees':[]}, None)):
            radar._validate_candidate(item, {}, 1)
        self.assertEqual(item['status'], 'Skip')
    def test_competition(self):
        item=radar.evaluate(self.issue())
        with patch.object(radar, '_github_get', side_effect=[({'state':'open','assignees':[]}, None), ([],None), ([{'body':'/claim this issue', 'html_url':'https://github.com/example/repo/issues/1#issuecomment-1'}],None)]):
            radar._validate_candidate(item, {}, 1)
        self.assertEqual(item['status'], 'Hold / verify')
        self.assertEqual(item['competition']['claim_comment_count'], 1)

if __name__=='__main__': unittest.main()
