import unittest
from unittest.mock import MagicMock, patch
import json
import re

# ==========================================
# 1. CORE LOGIC (The "Brain" Functions)
# ==========================================

def clean_json_text(text):
    """Removes markdown backticks if LLM adds them."""
    if not text: return "{}"
    # Regex to strip markdown code blocks
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
    return text.strip()

def analyze_and_plan_research(client, transcript_text):
    """Phase 1: Strategist (Gemini) identifies gaps."""
    prompt = "Analyze transcript and return JSON research plan."
    
    # Using the public 2.0 Flash Experimental model
    response = client.models.generate_content(
        model='gemini-2.0-flash-exp', 
        contents=[{"parts": [{"text": f"{prompt}\n\nTRANSCRIPT:\n{transcript_text}"}]}]
    )
    # Extract text safely
    try:
        raw_text = response.candidates[0].content.parts[0].text
    except (AttributeError, IndexError):
        raw_text = "{}"
        
    return json.loads(clean_json_text(raw_text))

def execute_research_plan(plan):
    """Phase 2: Scout (Sonar) executes the plan."""
    # Stub for testing logic flow
    results = []
    for q in plan.get('research_questions', []):
        results.append(f"Q: {q}")
    return results

def synthesize_knowledge(client, transcript, research_data):
    """Phase 3: Architect (Gemini) merges data."""
    prompt = "Synthesize Graph JSON and Markdown Brief."
    
    response = client.models.generate_content(
        model='gemini-2.0-flash-exp', 
        contents=[{"parts": [{"text": f"{prompt}\n{transcript}\n{research_data}"}]}]
    )
    
    try:
        raw_text = response.candidates[0].content.parts[0].text
    except (AttributeError, IndexError):
        raw_text = "{}"
        
    return json.loads(clean_json_text(raw_text))

# ==========================================
# 2. TEST SUITE
# ==========================================

class TestProfitGraphStandalone(unittest.TestCase):
    
    def setUp(self):
        """Mock data for simulation."""
        self.mock_transcript = "DeepSeek-V3 helps with training stability."
        
        self.mock_plan = {
            "core_topic": "DeepSeek",
            "research_questions": ["Cost?", "Implementation?"]
        }
        self.mock_final = {
            "graph_data": {"nodes": [{"id": "DeepSeek", "type": "Tool"}]},
            "markdown_brief": "# Strategy Brief"
        }

    def test_json_cleaner(self):
        """Verifies the regex cleaner."""
        # FIXED: Concatenated string to prevent paste errors in Termux
        part1 = "```json\n"
        part2 = '{"key": "value"}'
        part3 = "\n```"
        dirty = part1 + part2 + part3
        
        cleaned = clean_json_text(dirty)
        parsed = json.loads(cleaned)
        self.assertEqual(parsed['key'], 'value')

    @patch('google.genai.Client') 
    def test_strategist_logic(self, MockClient):
        """Tests Phase 1 with CORRECT mocking."""
        print("\n[1/3] Testing Strategist...")
        
        mock_cli = MockClient.return_value
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = json.dumps(self.mock_plan)
        
        # Mock the nested response structure of the SDK
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]
        
        mock_cli.models.generate_content.return_value = mock_response
        
        plan = analyze_and_plan_research(mock_cli, self.mock_transcript)
        
        self.assertEqual(plan["core_topic"], "DeepSeek")
        print("✅ Strategist Logic Passed")

    @patch('google.genai.Client')
    def test_architect_logic(self, MockClient):
        """Tests Phase 3 Synthesis."""
        print("[2/3] Testing Architect...")
        
        mock_cli = MockClient.return_value
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = json.dumps(self.mock_final)
        
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]
        
        mock_cli.models.generate_content.return_value = mock_response
        
        final_output = synthesize_knowledge(mock_cli, self.mock_transcript, "Research Data")
        
        self.assertIn("graph_data", final_output)
        print("✅ Architect Logic Passed")

    def test_scout_logic(self):
        """Tests Phase 2 iteration logic."""
        print("[3/3] Testing Scout Loop...")
        plan = {"research_questions": ["Q1", "Q2"]}
        results = execute_research_plan(plan)
        self.assertEqual(len(results), 2)
        print("✅ Scout Logic Passed")

if __name__ == '__main__':
    unittest.main()



