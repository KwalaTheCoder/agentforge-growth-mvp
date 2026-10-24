import unittest
from gmail_delivery import validate_recipient, build_message, send_once, fingerprint
class TestGmail(unittest.TestCase):
 def test_valid(self): self.assertEqual(validate_recipient('a@example.org'),'a@example.org')
 def test_invalid(self):
  for x in ['a@example.org,b@example.org','Bad <a@example.org>','a@b','x\ny@example.org']:
   with self.assertRaises(ValueError): validate_recipient(x)
 def test_message(self): self.assertIn('raw',build_message('a@example.org','Hello','Body'))
 def test_approval(self):
  with self.assertRaises(PermissionError): send_once('a@example.org','x','y',approved=False,consent_basis='yes')
 def test_fingerprint(self): self.assertEqual(fingerprint('a@example.org','a','b'),fingerprint('a@example.org','a','b'))
if __name__=='__main__': unittest.main()
