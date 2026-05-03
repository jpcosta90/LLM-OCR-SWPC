import os
import csv
import base64
import requests
import time
from tqdm import tqdm

# Configuration
OLLAMA_BASE = "http://localhost:11434"
OLLAMA_GEN = f"{OLLAMA_BASE}/api/generate"
OLLAMA_PULL = f"{OLLAMA_BASE}/api/pull"
OLLAMA_DEL = f"{OLLAMA_BASE}/api/delete"

IMAGES_DIR = "data/raw2"
GROUND_TRUTH_CSV = "data/ground_truth/raw2/raw2_manual_ocr_ground_truth.csv"
OUTPUT_DIR = "data/results/stability_experiment/ollama_outputs"
N_ROUNDS = 100

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

def run_stability_inference(model_name, ground_truth_images):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    model_safe_name = model_name.replace("/", "_").replace(":", "_")
    model_output_dir = os.path.join(OUTPUT_DIR, model_safe_name)
    os.makedirs(model_output_dir, exist_ok=True)

    for img in ground_truth_images:
        img_path = os.path.join(IMAGES_DIR, img)
        if not os.path.exists(img_path):
            continue
            
        print(f"\nProcessing {img} (100 rounds)...")
        img_b64 = encode_image(img_path)
        
        for i in tqdm(range(N_ROUNDS), desc=f"{img} ({model_name})"):
            base_name = os.path.splitext(img)[0]
            filename = os.path.join(model_output_dir, f"{base_name}_round_{i+1}.txt")
            
            if os.path.exists(filename):
                continue
                
            success = False
            for attempt in range(3):
                try:
                    payload = {
                        "model": model_name,
                        "prompt": "Extract the text from this image.",
                        "system": SYSTEM_PROMPT,
                        "images": [img_b64],
                        "stream": False,
                        "keep_alive": "10m",
                        "options": {
                            "temperature": 0.0, # Will be overridden by do_sample if >0, but kept 0 for greedy baseline stability test
                            "num_predict": 1536,
                            "repeat_penalty": 1.4,
                            "top_k": 40,
                            "top_p": 0.9
                        }
                    }
                    
                    # Force do_sample like HF if we want actual variance across 100 rounds
                    # Ollama's temperature 0.8 is good for slight variance
                    payload["options"]["temperature"] = 0.8 
                    
                    res = requests.post(OLLAMA_GEN, json=payload, timeout=600)
                    
                    if res.status_code == 200:
                        prediction = res.json().get("response", "").strip()
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(prediction)
                        success = True
                        break
                except Exception:
                    time.sleep(2)
            
            if not success:
                # Save empty file to prevent infinite retries on completely broken models
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("")

def check_model_completed(model_name, ground_truth_images):
    model_safe_name = model_name.replace("/", "_").replace(":", "_")
    model_output_dir = os.path.join(OUTPUT_DIR, model_safe_name)
    if not os.path.exists(model_output_dir):
        return False
    
    expected_files = len(ground_truth_images) * N_ROUNDS
    actual_files = len([f for f in os.listdir(model_output_dir) if f.endswith('.txt')])
    return actual_files >= expected_files

def main():
    ground_truth_images = []
    if os.path.exists(GROUND_TRUTH_CSV):
        with open(GROUND_TRUTH_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            ground_truth_images = [row['filename'] for row in reader]
    
    if not ground_truth_images:
        print("No ground truth found.")
        return

    for model in MODELS:
        print(f"\n{'='*50}\nTARGET: {model}\n{'='*50}")
        if check_model_completed(model, ground_truth_images):
            print(f"Skipping {model} - All rounds already completed.")
            continue
            
        if manage_remote_model("pull", model):
            run_stability_inference(model, ground_truth_images)
            manage_remote_model("delete", model)

if __name__ == "__main__":
    main()
