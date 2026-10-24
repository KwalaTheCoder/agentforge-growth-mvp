"""Regression tests for missing-evidence qualification and persisted stages."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class QualificationRegression(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        spec=importlib.util.spec_from_file_location('direct_b2b_regression', ROOT/'direct_b2b.py')
        self.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.module.DB=Path(self.temp.name)/'leads.sqlite3'
        self.row=dict(source_url='https://github.com/epilot-dev',company='epilot',website='',country='Germany',description='',service='AI / Automation',need_evidence='',evidence_url='',contact_channel='',contact_permission_checked=False,identity_checked=False,need_checked=False,stage='Research',notes='',draft='',followup='')

    def test_missing_evidence_cannot_qualify(self):
        self.module.save(self.row)
        with self.assertRaises(ValueError):
            self.module.save(dict(self.row,stage='Qualified'))
        self.assertEqual(self.module.all_prospects()[0]['stage'],'Research')

    def test_checked_boxes_do_not_replace_missing_evidence(self):
        self.module.save(self.row)
        with self.assertRaises(ValueError):
            self.module.save(dict(self.row,stage='Qualified',identity_checked=True,need_checked=True,contact_permission_checked=True))
        self.assertEqual(self.module.all_prospects()[0]['stage'],'Research')

    def test_valid_qualification_persists_and_can_revert(self):
        qualified=dict(self.row,stage='Qualified',identity_checked=True,need_checked=True,contact_permission_checked=True,need_evidence='Documented public request',evidence_url='https://example.com/request',contact_channel='Verified public business contact form')
        self.module.save(qualified)
        self.assertEqual(self.module.all_prospects()[0]['stage'],'Qualified')
        self.module.save(dict(qualified,stage='Research'))
        self.assertEqual(self.module.all_prospects()[0]['stage'],'Research')

if __name__=='__main__': unittest.main()
