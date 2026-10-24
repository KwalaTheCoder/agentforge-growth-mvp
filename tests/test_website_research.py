import unittest
from unittest.mock import Mock
from website_research import validate_site, inspect_homepage, TextOnly

class WebsiteResearchTests(unittest.TestCase):
    def test_reject_unsafe(self):
        for url in ('http://example.com','https://127.0.0.1','https://localhost',
                    'https://example.com:8443','file:///etc/passwd','https://user:pass@example.com',
                    'https://a.local'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_site(url)

    def test_domain(self):
        self.assertEqual(validate_site('https://iterate.ai/solutions?q=1'), ('iterate.ai','/solutions?q=1'))

    def test_extract(self):
        p=TextOnly();p.feed('<title>Example</title><script>bad()</script><p>Hello world</p>')
        self.assertEqual(''.join(p.title),'Example')
        self.assertNotIn('bad()', ''.join(p.parts))

    def test_pinned_fetch(self):
        response=Mock(status=200)
        response.getheader.side_effect=lambda k,default='': {'Content-Type':'text/html','Content-Length':'42'}.get(k,default)
        response.read.return_value=b'<title>Test</title><p>Public information</p>'
        connection=Mock();connection.getresponse.return_value=response
        factory=Mock(return_value=connection)
        result=inspect_homepage('https://example.com',connector=factory,resolver=lambda h:['93.184.215.14'])
        self.assertEqual(result['page_title'],'Test')
        self.assertIn('Public information',result['public_page_excerpt'])
        factory.assert_called_once_with('example.com','93.184.215.14',timeout=8)
        connection.close.assert_called_once()

    def test_redirect_blocked(self):
        response=Mock(status=302)
        connection=Mock();connection.getresponse.return_value=response
        with self.assertRaisesRegex(ValueError,'redirect'):
            inspect_homepage('https://example.com',connector=lambda *a,**k:connection,
                             resolver=lambda h:['93.184.215.14'])
        connection.close.assert_called_once()

if __name__=='__main__': unittest.main()
