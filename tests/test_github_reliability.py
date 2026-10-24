import tempfile
import unittest
from unittest.mock import Mock
from github_reliability import GitHubClient,RateLimited

class ReliabilityTests(unittest.TestCase):
    def test_cache_reuse(self):
        with tempfile.TemporaryDirectory() as d:
            response=Mock(status_code=200,headers={},json=lambda:{'items':[1]})
            client=GitHubClient(session=Mock(get=Mock(return_value=response)),cache_dir=d,now=lambda:1000)
            self.assertEqual(client.get('https://api.github.com/search/issues'),{'items':[1]})
            self.assertEqual(client.get('https://api.github.com/search/issues'),{'items':[1]})
            self.assertEqual(client.session.get.call_count,1)
    def test_rate_limit_stops_network(self):
        with tempfile.TemporaryDirectory() as d:
            response=Mock(status_code=403,headers={'Retry-After':'120'})
            client=GitHubClient(session=Mock(get=Mock(return_value=response)),cache_dir=d,now=lambda:1000)
            with self.assertRaises(RateLimited): client.get('https://api.github.com/repos/a/b/issues/1')
            with self.assertRaises(RateLimited): client.get('https://api.github.com/repos/a/b/issues/2')
            self.assertEqual(client.session.get.call_count,1)
    def test_reject_external(self):
        with tempfile.TemporaryDirectory() as d:
            client=GitHubClient(cache_dir=d)
            with self.assertRaises(ValueError): client.get('https://evil.test/data')
if __name__=='__main__':unittest.main()
