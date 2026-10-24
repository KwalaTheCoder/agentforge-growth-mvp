import unittest
from unittest.mock import patch, Mock
from direct_b2b import clean_ollama_answer, research_prompt, ollama_generate

class ResearchV2Tests(unittest.TestCase):
    def test_stray_closing_think_tag(self):
        self.assertEqual(clean_ollama_answer('</think>\n\n**Research Memo**'), '**Research Memo**')

    def test_full_thinking_block(self):
        self.assertEqual(clean_ollama_answer('<think>private\nreasoning</think>\nAnswer'), 'Answer')

    def test_unclosed_think_not_leaked(self):
        self.assertEqual(clean_ollama_answer('<think>unfinished'), '')

    def test_research_prompt_limits_services(self):
        p = research_prompt({'company':'epilot','source_url':'https://github.com/epilot-dev'})
        self.assertIn('at most THREE concrete services', p)
        self.assertIn('No documented buyer need', p)
        self.assertIn('CI-CD', p)

    @patch('direct_b2b.requests.post')
    def test_ollama_sends_no_think_and_cleans_output(self, post):
        post.return_value = Mock()
        post.return_value.json.return_value = {'response':'</think>\nREADY','done_reason':'stop'}
        self.assertEqual(ollama_generate('test'), 'READY')
        payload = post.call_args.kwargs['json']
        self.assertFalse(payload['think'])
        self.assertTrue(payload['prompt'].startswith('/no_think\n'))

if __name__ == '__main__':
    unittest.main()
