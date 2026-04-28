import os
import csv
import json
import base64
import requests
import time
from datetime import datetime

# Configuration
OLLAMA_URL = "http://168.138.70.52:11434/api/generate"
OLLAMA_TAGS_URL = "http://168.138.70.52:11434/api/tags"
DATASET_CSV = "data/ground_truth/dataset_mirror_v1.csv"
IMAGE_DIR = "data/raw/parallel_clean"
RESULTS_DIR = "data/results/raw_predictions"

# Models to test
MODELS = [
    "minicpm-v:8b",
    "qwen3.5:2b",
    "qwen3.5:4b",
    "qwen3.5:9b",
    "blaifa/InternVL3_5:4B",
    "blaifa/InternVL3_5:8b",
    "granite3.2-vision:2b",
    "gemma4:e2b",
    "gemma4:e4b"
] 

SYSTEM_PROMPT = "You are a highly accurate OCR system. Your task is to extract all the text from the provided image exactly as it appears. Output ONLY the extracted text. Do not include any introductory or concluding remarks."

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_installed_models():
    try:
        res = requests.get(OLLAMA_TAGS_URL, timeout=10)
        return [m['name'] for m in res.json().get('models', [])]
    except:
        return []

def run_benchmark():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # Load dataset
    samples = []
    with open(DATASET_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        samples = [row for row in reader]
    
    print(f"Loaded {len(samples)} parallel samples.")
    
    installed_models = get_installed_models()
    
    for model in MODELS:
        # Check if model is ready
        if model not in installed_models:
            print(f"Skipping {model} (Not yet pulled/installed)")
            continue
            
        print(f"\nBenchmarking Model: {model}")
        
        model_results_path = os.path.join(RESULTS_DIR, f"{model.replace('/', '_').replace(':', '_')}_results.csv")
        
        # Check for resume
        completed_files = set()
        if os.path.exists(model_results_path):
            with open(model_results_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                completed_files = {row['filename'] for row in reader}
        
        # Open results file in append mode
        with open(model_results_path, "a", encoding="utf-8", newline="") as f:
            fieldnames = ["filename", "language", "topic", "ground_truth", "prediction", "timestamp"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not completed_files:
                writer.writeheader()
            
            for i, sample in enumerate(samples):
                if sample['filename'] in completed_files:
                    continue
                
                img_path = os.path.join(IMAGE_DIR, sample['filename'])
                if not os.path.exists(img_path):
                    print(f"  Warning: File {img_path} not found.")
                    continue
                
                print(f"  [{i+1}/{len(samples)}] Processing {sample['filename']}...", end="", flush=True)
                
                try:
                    img_b64 = encode_image(img_path)
                    
                    payload = {
                        "model": model,
                        "prompt": "Extract the text from this image.",
                        "system": SYSTEM_PROMPT,
                        "images": [img_b64],
                        "stream": False,
                        "options": {"temperature": 0.0}
                    }
                    
                    start_time = time.time()
                    response = requests.post(OLLAMA_URL, json=payload, timeout=300)
                    elapsed = time.time() - start_time
                    
                    if response.status_code == 200:
                        prediction = response.json().get("response", "").strip()
                        writer.writerow({
                            "filename": sample['filename'],
                            "language": sample['language'],
                            "topic": sample['topic'],
                            "ground_truth": sample['text'],
                            "prediction": prediction,
                            "timestamp": datetime.now().isoformat()
                        })
                        f.flush()
                        print(f" Done ({elapsed:.2f}s)")
                    else:
                        print(f" Failed ({response.status_code})")
                except Exception as e:
                    print(f" Error: {e}")
                
                # Small sleep between requests to allow CPU cooling (optional)
                # time.sleep(1)

if __name__ == "__main__":
    run_benchmark()
