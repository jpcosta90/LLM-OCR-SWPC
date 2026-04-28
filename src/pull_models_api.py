import requests
import json
import os

# Configuration
OLLAMA_BASE_URL = "http://168.138.70.52:11434"
PULL_URL = f"{OLLAMA_BASE_URL}/api/pull"

MODELS = [
    "moondream",
    "qwen2-vl:2b",
    "qwen2-vl:7b",
    "blaifa/internvl2:2b",
    "blaifa/internvl2:4b",
    "blaifa/internvl2:8b",
    "llava:7b",
    "llava:13b",
    "llama3.2-vision:11b",
    "erwan2/Janus-1.3B",
    "deepseek-janus:7b"
]

def pull_models():
    print(f"Starting remote pull of {len(MODELS)} models via API...")
    
    for model in MODELS:
        print(f"Pulling {model}...")
        payload = {"name": model, "stream": False}
        try:
            # We use stream=True even if payload says False to handle the potential long-lived connection
            response = requests.post(PULL_URL, json=payload, timeout=3600)
            if response.status_code == 200:
                print(f"  Successfully pulled {model}")
            else:
                print(f"  Failed to pull {model}: {response.text}")
        except Exception as e:
            print(f"  Error pulling {model}: {e}")

if __name__ == "__main__":
    pull_models()
