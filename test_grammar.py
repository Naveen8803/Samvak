import unittest
from unittest.mock import patch, MagicMock
from grammar_helper import gloss_to_english
import os

class TestGrammarHelper(unittest.TestCase):
    
    @patch('grammar_helper.genai.GenerativeModel')
    def test_gloss_to_english_success(self, mock_model_class):
        # Mock the API response
        mock_model = mock_model_class.return_value
        mock_response = MagicMock()
        mock_response.text = "I want water."
        mock_model.generate_content.return_value = mock_response
        
        # Test input
        glosses = ["ME", "WANT", "WATER"]
        result = gloss_to_english(glosses)
        
        self.assertEqual(result, "I want water.")
        
    @patch('grammar_helper.genai.GenerativeModel')
    def test_gloss_to_english_empty(self, mock_model_class):
        result = gloss_to_english([])
        self.assertEqual(result, "")

    # We can add more tests if needed, but this covers the basic logic.

if __name__ == '__main__':
    # Set a dummy key for testing so it doesn't fail on the key check if env var is missing
    if "GEMINI_API_KEY" not in os.environ:
        os.environ["GEMINI_API_KEY"] = "dummy_key_for_test"
        
    unittest.main()
