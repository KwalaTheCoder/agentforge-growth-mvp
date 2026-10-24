import json
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from release_tools.final_integration import MODULES, audit, backup_tasks, readonly_status, verify_tasks

class FinalIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in MODULES:
            file=self.root/name
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text("# fixture",encoding="utf-8")
        for dbname,table in (("leads.sqlite3","b2b_v20_prospects"),("operations.sqlite3","growth_tasks")):
            with closing(sqlite3.connect(self.root/dbname)) as db:
                db.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")
                db.execute(f"INSERT INTO {table} DEFAULT VALUES")
                db.commit()
    def test_audit(self):
        self.assertTrue(audit(self.root)["ok"])
        self.assertEqual(audit(self.root)["tasks"]["records"],1)
    def test_missing_module(self):
        (self.root/"growth_operations.py").unlink()
        self.assertFalse(audit(self.root)["ok"])
    def test_missing_tasks_no_create(self):
        (self.root/"operations.sqlite3").unlink()
        self.assertFalse(audit(self.root)["ok"])
        self.assertFalse((self.root/"operations.sqlite3").exists())
    def test_task_backup(self):
        path=backup_tasks(self.root)
        self.assertEqual(verify_tasks(path)["filename"],path.name)
    def test_task_backup_tamper(self):
        path=backup_tasks(self.root)
        with path.open("ab") as file: file.write(b"bad")
        with self.assertRaises(ValueError):verify_tasks(path)
    def test_no_crm_mutation(self):
        before=(self.root/"leads.sqlite3").read_bytes()
        audit(self.root)
        backup_tasks(self.root)
        self.assertEqual(before,(self.root/"leads.sqlite3").read_bytes())
