import tempfile
import unittest
from pathlib import Path
from datetime import date
from daily_operations import create_task,list_tasks,update_task,summarize

class DailyOperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/'operations.sqlite3'
    def add(self,**kwargs):
        return create_task('Verify company identity','Founder 1','Company research',path=self.db,**kwargs)
    def test_create_persists(self):
        i=self.add()
        self.assertEqual(list_tasks(self.db)[0]['id'],i)
    def test_assign_and_finish(self):
        i=self.add()
        update_task(i,owner='Founder 2',status='Done',path=self.db)
        self.assertEqual(list_tasks(self.db)[0]['status'],'Done')
        self.assertEqual(summarize(list_tasks(self.db))['open'],0)
    def test_due_and_overdue(self):
        self.add(due_date='2026-01-01')
        self.assertEqual(summarize(list_tasks(self.db),date(2026,1,2))['overdue'],1)
    def test_bad_date(self):
        with self.assertRaises(ValueError): self.add(due_date='tomorrow')
    def test_bad_owner(self):
        with self.assertRaises(ValueError): create_task('Research','Random','Company research',path=self.db)
    def test_invalid_url(self):
        with self.assertRaises(ValueError): self.add(source_url='file:///secret')
    def test_missing_task(self):
        with self.assertRaises(ValueError): update_task(999,owner='Founder 1',status='Done',path=self.db)
    def test_no_crm_created(self):
        self.add()
        self.assertFalse((self.db.parent/'leads.sqlite3').exists())
    def test_bad_status(self):
        i=self.add()
        with self.assertRaises(ValueError): update_task(i,owner='Founder 1',status='Qualified',path=self.db)
