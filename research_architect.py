import os
import json
import requests
import argparse
import re
from typing import Optional, Dict, Any

class ResearchArchitect:
    def __init__(self, model: str = "gemma4:e2b"):
        self.model = model
        self.url = self._load_url()

    def _load_url(self):
        # Prefer OLLAMA_URL from .env or environment
        if os.path.exists(".env"):
            with open(".env") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        if k.strip() == "OLLAMA_URL":
                            url = v.strip().rstrip("/")
                            return f"{url}/api/generate"
        
        env_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        return f"{env_url.rstrip('/')}/api/generate"

    def call_ollama(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        print(f"\n--- Calling Ollama ({self.model}) ---")
        full_prompt = f"System: {system_prompt}\nUser: {user_prompt}"
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": True,
            "options": {"temperature": 0.3}
        }
        
        response_text = ""
        try:
            res = requests.post(self.url, json=payload, timeout=1200, stream=True)
            res.raise_for_status()
            
            for line in res.iter_lines():
                if line:
                    chunk = json.loads(line.decode('utf-8'))
                    token = chunk.get('response', '')
                    if token:
                        print(token, end='', flush=True)
                        response_text += token
                    if chunk.get('done'): print("\n")
            
            return response_text
        except Exception as e:
            print(f"\nError in Ollama call: {e}")
            return None

    def refine_question(self, need: str) -> Dict[str, Any]:
        system_prompt = """You are a Senior Research Architect specializing in Systematic Literature Reviews and Meta-Analysis.
Your task is to transform a vague research need into a HIGHLY FORMAL and SCIENTIFIC Research Question.

LANGUAGE REQUIREMENT: All outputs MUST be in English, regardless of the input language.

Logical Process:
1. DECONSTRUCTION: Identify the PICO components (Population, Intervention, Comparison, Outcome).
2. SYNTHESIS: Formulate a precise, measurable, and academically rigorous Research Question.

Scientific Rigor Guidelines:
- PRECISION: Avoid generic phrases like "What is the comparison" or "How does it compare". Use "To what extent and in what manner...", "Evaluate the comparative effectiveness of...", "Analyze the correlation between...", or "Assess the trade-off between X and Y".
- MEASURABILITY: The question must point towards specific empirical variables (e.g., throughput, cost-efficiency, accuracy, latency, scalability).
- FORMALITY: Use technical terminology and academic syntax.
- SPECIFICITY: Avoid broad generalizations; focus on the concrete boundaries of the PICO.

Examples:
- POOR: "What is the comparison between local and cloud LLMs for sentiment analysis?"
- EXCELLENT: "To what extent do localized LLM deployments (1-7B parameters) impact latency and data privacy versus cloud-based architectures in real-time sentiment classification of high-velocity social media streams?"

Output Format:
You must return your analysis as a JSON object with this EXACT structure (PICO first, then RQ):
{
  "pico": {
    "population": "...",
    "intervention": "...",
    "comparison": "...",
    "outcome": "..."
  },
  "research_question": "The refined, highly formal scientific research question"
}
Return ONLY the JSON object. No preamble, no explanation, no backticks outside the JSON.
ALWAYS OUTPUT IN ENGLISH."""

        user_prompt = f"Research Need: {need}"
        
        response = self.call_ollama(system_prompt, user_prompt)
        if response:
            try:
                # Robust extraction of JSON from response
                match = re.search(r"(\{.*\})", response, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    return json.loads(json_str)
                else:
                    raise ValueError("No JSON object found in response")
            except Exception as e:
                print(f"\n[ERROR] Failed to parse JSON: {e}")
                return {"error": "JSON parsing failed", "raw": response}
        return {"error": "No response from model"}

    def save_config(self, data: Dict[str, Any], output_path: str):
        # Sanitize review name from RQ or use default
        review_name = "Automated Review"
        if "research_question" in data:
            # Simple sanitization
            words = data["research_question"].split()[:5]
            review_name = "_".join(re.sub(r'[^a-zA-Z0-9]', '', w).lower() for w in words)

        config = {
            "review_name": review_name,
            "pico_framework": data.get("pico", {}),
            "research_question": data.get("research_question", ""),
            "criteria": {"inclusion": [], "exclusion": []},
            "apis_to_use": ["arxiv", "dblp", "openalex"],
            "max_results_per_api": 1000
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        print(f"\n✅ Configuration saved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Architect a Research Question from a raw need using local LLM.")
    parser.add_argument("--need", required=True, help="The research need or problem description")
    parser.add_argument("--output", help="Path to save the generated config (default: reviews/new_project/config.json)")
    parser.add_argument("--model", default="gemma4:e2b", help="Ollama model name (default: gemma4:e2b)")
    args = parser.parse_args()

    # Default output path handling
    output_path = args.output
    if not output_path:
        output_path = "reviews/new_project/config.json"

    architect = ResearchArchitect(model=args.model)
    print(f"🧐 Architecting research question for: '{args.need}'")
    result = architect.refine_question(args.need)
    
    if "error" not in result:
        architect.save_config(result, output_path)
    else:
        print(f"❌ Failed to architect research question: {result.get('error')}")
        if result.get("raw"):
            print(f"Raw response was captured for debugging.")
