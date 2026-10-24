import tempfile
import unittest
from pathlib import Path
from release_tools.security_audit import audit
class SecurityAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'.streamlit').mkdir()
        (self.root/'.streamlit/config.toml').write_text('[server]\naddress = "127.0.0.1"\nenableCORS = true\nenableXsrfProtection = true\n')
        (self.root/'.gitignore').write_text('leads.sqlite3\nleads.sqlite3-wal\nleads.sqlite3-shm\n.env\n.streamlit/secrets.toml\nbackups/\n')
    def test_good(self):
        self.assertTrue(audit(self.root)['ready_for_local_review'])
    def test_missing_gitignore(self):
        (self.root/'.gitignore').unlink()
        self.assertFalse(audit(self.root)['ready_for_local_review'])
    def test_public_binding(self):
        (self.root/'.streamlit/config.toml').write_text('[server]\naddress = "0.0.0.0"\n')
        self.assertFalse(audit(self.root)['ready_for_local_review'])
    def test_xsrf_disabled(self):
        (self.root/'.streamlit/config.toml').write_text('[server]\naddress = "127.0.0.1"\nenableXsrfProtection = false\n')
        self.assertFalse(audit(self.root)['ready_for_local_review'])
    def test_no_secret_values_read(self):
        (self.root/'.env').write_text('API_KEY=DO_NOT_PRINT_THIS')
        self.assertNotIn('DO_NOT_PRINT_THIS',str(audit(self.root)))
