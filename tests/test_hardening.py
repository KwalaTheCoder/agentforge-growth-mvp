import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/'leads.sqlite3'
        self.b=load('direct_b2b')
        self.f=load('followup_dashboard')
        self.b.DB=self.db
        self.f.DB=self.db
        self.source='https://github.com/example-company'
        self.base=dict(source_url=self.source,company='Example',website='',country='',description='',service='AI / Automation',need_evidence='Public need',evidence_url='https://example.com/need',contact_channel='public business form',contact_permission_checked=True,identity_checked=True,need_checked=True,stage='Qualified',notes='',draft='',followup='')
        self.b.save(self.base)

    def test_unverified_cannot_qualify(self):
        item=dict(self.base,need_checked=False)
        with self.assertRaises(ValueError): self.b.save(item)

    def test_no_stage_jump_to_won(self):
        with self.assertRaises(ValueError): self.b.save(dict(self.base,stage='Won'))

    def test_invalid_followup_date(self):
        with self.assertRaises(ValueError): self.b.save(dict(self.base,followup='2026-99-99'))

    def test_research_note_does_not_erase_due(self):
        self.f.save_event('B2B',self.source,'Research note','2026-01-01','2026-01-02','Call later')
        self.f.save_event('B2B',self.source,'Research note','2026-01-03','','Research update')
        self.assertEqual(len(self.f.dashboard()['due']),1)

    def test_no_double_revenue(self):
        self.f.save_event('B2B',self.source,'Won','2026-01-01',note='Signed contract',amount_realized=100,currency='USD')
        with self.assertRaises(ValueError):
            self.f.save_event('B2B',self.source,'Won','2026-01-02',note='Repeated contract',amount_realized=100,currency='USD')
        self.assertEqual(self.f.dashboard()['revenue']['USD'],100)

    def test_invalid_money(self):
        for value in (float('nan'),float('inf'),-1,0):
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.f.save_event('B2B',self.source,'Won','2026-01-01',note='Signed',amount_realized=value,currency='USD')

    def test_no_contact_before_qualification(self):
        self.b.save(dict(self.base,stage='Research',identity_checked=False))
        with self.assertRaises(ValueError):
            self.f.save_event('B2B',self.source,'Contact sent','2026-01-01',note='Sent manually')

if __name__=='__main__': unittest.main()
