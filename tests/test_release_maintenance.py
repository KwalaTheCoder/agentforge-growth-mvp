import json
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from release_tools.maintenance import backup, check_db, doctor, restore, verify_backup, REQUIRED

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for name in REQUIRED:
            p=self.root/name
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text("fixture")
        with closing(sqlite3.connect(self.root/"leads.sqlite3")) as con:
            con.execute("CREATE TABLE b2b_v20_prospects (source_url TEXT)")
            con.execute("INSERT INTO b2b_v20_prospects VALUES ('fixture')")
            con.commit()
    def test_doctor(self):
        self.assertTrue(doctor(self.root)["ok"])
    def test_backup_verify(self):
        target=backup(self.root)
        self.assertTrue(target.exists())
        self.assertTrue(verify_backup(target)["sha256"])
    def test_restore_requires_confirmation(self):
        target=backup(self.root)
        with self.assertRaises(ValueError):
            restore(self.root,target)
    def test_restore_reverts_data(self):
        target=backup(self.root)
        with closing(sqlite3.connect(self.root/"leads.sqlite3")) as con:
            con.execute("INSERT INTO b2b_v20_prospects VALUES ('new')")
            con.commit()
        restore(self.root,target,True)
        with closing(sqlite3.connect(self.root/"leads.sqlite3")) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM b2b_v20_prospects").fetchone()[0],1)
    def test_tampering_detected(self):
        target=backup(self.root)
        with open(target,"ab") as f:f.write(b"tampered")
        with self.assertRaises(ValueError):
            verify_backup(target)
    def test_no_database(self):
        (self.root/"leads.sqlite3").unlink()
        self.assertFalse(doctor(self.root)["ok"])
