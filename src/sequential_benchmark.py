import os
import csv
import json
import base64
import requests
import time
from datetime import datetime

# Configuration
OLLAMA_BASE = "http://localhost:11434"
OLLAMA_GEN = f"{OLLAMA_BASE}/api/generate"
OLLAMA_PULL = f"{OLLAMA_BASE}/api/pull"
OLLAMA_DEL = f"{OLLAMA_BASE}/api/delete"

DATASET_CSV = "data/ground_truth/dataset_mirror_v1.csv"
IMAGE_DIR = "data/raw/parallel_clean"
RESULTS_DIR = "data/results/raw_predictions"

# Verified Models for the Benchmark
MODELS = [
    "granite3.2-vision:2b",
    "ministral-3:3b",
    "ministral-3:8b",
    "qwen3.5:2b",
    "qwen3.5:4b",
    "qwen3.5:9b",
    "blaifa/InternVL3_5:4B",
    "blaifa/InternVL3_5:8b",
    "gemma4:e2b",
    "gemma4:e4b"
] 

SYSTEM_PROMPT = "You are a highly accurate OCR system. Your task is to extract all the text from the provided image exactly as it appears. Output ONLY the extracted text. Do not include any introductory or concluding remarks."

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def manage_remote_model(action, model_name):
    """Handles PULL or DELETE on the remote Ollama server."""
    payload = {"name": model_name, "stream": False}
    
    print(f"[{action.upper()}] {model_name}...", end="", flush=True)
    try:
        if action == "pull":
            res = requests.post(OLLAMA_PULL, json=payload, timeout=3600)
        else:
            res = requests.delete(OLLAMA_DEL, json=payload, timeout=120)
            
        if res.status_code == 200:
            print(" Success")
            return True
        else:
            print(f" Failed ({res.status_code}): {res.text}")
            return False
    except Exception as e:
        print(f" Error: {e}")
        return False

def run_inference_batch(model_name, samples):
    """Runs OCR for all 162 samples using the loaded model."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    model_safe_name = model_name.replace("/", "_").replace(":", "_")
    results_path = os.path.join(RESULTS_DIR, f"{model_safe_name}_results.csv")
    
    # Check for resume
    completed_files = set()
    if os.path.exists(results_path):
        with open(results_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            completed_files = {row['filename'] for row in reader}

    with open(results_path, "a", encoding="utf-8", newline="") as f:
        fieldnames = ["filename", "language", "topic", "ground_truth", "prediction", "timestamp"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not completed_files:
            writer.writeheader()

        for i, sample in enumerate(samples):
            if sample['filename'] in completed_files:
                continue
            
            img_path = os.path.join(IMAGE_DIR, sample['filename'])
            if not os.path.exists(img_path): continue
            
            print(f"  ({i+1}/{len(samples)}) {sample['filename']}...", end="", flush=True)
            
            success = False
            for attempt in range(3): # 3 retries
                try:
                    img_b64 = encode_image(img_path)
                    payload = {
                        "model": model_name,
                        "prompt": "Extract the text from this image.",
                        "system": SYSTEM_PROMPT,
                        "images": [img_b64],
                        "stream": False,
                        "keep_alive": "10m",
                        "options": {
                            "temperature": 0.0,
                            "num_predict": 1536,  # Prevent infinite generation
                            "repeat_penalty": 1.2, # Avoid loops
                            "top_k": 40,
                            "top_p": 0.9
                        }
                    }
                    
                    start_t = time.time()
                    # 600s is enough if num_predict is limited
                    res = requests.post(OLLAMA_GEN, json=payload, timeout=600)
                    elapsed = time.time() - start_t
                    
                    if res.status_code == 200:
                        prediction = res.json().get("response", "").strip()
                        writer.writerow({
                            "filename": sample['filename'],
                            "language": sample['language'],
                            "topic": sample['topic'],
                            "ground_truth": sample['text'],
                            "prediction": prediction,
                            "timestamp": datetime.now().isoformat()
                        })
                        f.flush()
                        print(f" OK ({elapsed:.1f}s)")
                        success = True
                        break
                    else:
                        print(f" ERR ({res.status_code})", end="")
                except Exception as e:
                    print(f" ERR: {e}", end="")
                
                if attempt < 2:
                    print(f" (Retrying {attempt+1}/2)...", end="")
                    time.sleep(5)
            
            if not success:
                print(" | FAILED all attempts")

def cleanup_remote_orphans():
    """Deletes all models from the target list to ensure a clean state."""
    print("\n[PRE-CLEANUP] Ensuring remote server is empty...")
    try:
        res = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=10)
        if res.status_code == 200:
            installed = [m['name'] for m in res.json().get('models', [])]
            for model in MODELS:
                if model in installed:
                    manage_remote_model("delete", model)
        else:
            print(f"  Warning: Could not list models ({res.status_code})")
    except Exception as e:
        print(f"  Cleanup Warning: {e}")

def main():
    # Load dataset
    with open(DATASET_CSV, "r", encoding="utf-8") as f:
        samples = [row for row in csv.DictReader(f)]
    
    print(f"Starting Sequential Benchmark for {len(MODELS)} models...")
    
    # Pre-clean orphans
    cleanup_remote_orphans()
    
    for model in MODELS:
        print(f"\n{'='*50}\nTARGET: {model}\n{'='*50}")
        
        # 1. Pull
        if manage_remote_model("pull", model):
            # 2. Benchmark
            run_inference_batch(model, samples)
            # 3. Cleanup
            manage_remote_model("delete", model)
        else:
            print(f"Skipping {model} due to pull failure.")

if __name__ == "__main__":
    main()
