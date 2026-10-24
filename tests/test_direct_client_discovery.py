import unittest
from unittest.mock import patch
from direct_client_discovery import search_organizations, organization_research, research_to_crm_prefill, validate_login

class DirectClientTests(unittest.TestCase):
    def test_login_validation(self):
        for x in ('a/b','a?b','', '../bad'):
            with self.assertRaises(ValueError): validate_login(x)
    @patch('direct_client_discovery.CLIENT.get')
    def test_search_filters_users(self, get):
        get.return_value={'items':[{'login':'team-a','type':'Organization','html_url':'https://github.com/team-a'},
                                           {'login':'alice','type':'User'}]}
        self.assertEqual(len(search_organizations('Germany','saas',5)),1)
    @patch('direct_client_discovery.CLIENT.get')
    def test_research_not_buyer_proof(self, get):
        get.side_effect=[{'type':'Organization','name':'Team A','description':'Software'},
                         {'items':[{'title':'Fix docker deployment','body':'Pipeline error','html_url':'https://github.com/team-a/x/issues/1'}]}]
        data=organization_research('team-a')
        self.assertEqual(data['qualification'],'Research Only')
        self.assertFalse(data['buyer_need_verified'])
        self.assertIn('DevOps',data['signals'][0]['service_topics'])
        self.assertFalse(research_to_crm_prefill(data)['contact_permission_checked'])
    @patch('direct_client_discovery.CLIENT.get')
    def test_reject_nonorg(self,get):
        get.return_value={'type':'User'}
        with self.assertRaises(ValueError): organization_research('someone')
if __name__=='__main__': unittest.main()
