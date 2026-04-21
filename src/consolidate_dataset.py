import os
import csv

# Configuration
IMG_DIR = "data/raw/parallel_clean"
GT_DIR = "data/ground_truth/parallel_clean"
OUTPUT_CSV = "data/ground_truth/dataset_mirror_v1.csv"

def consolidate():
    files = [f for f in os.listdir(IMG_DIR) if f.endswith(".png")]
    files.sort()
    
    rows = []
    for f in files:
        lang_topic = f.replace(".png", "")
        parts = lang_topic.split("_", 1)
        lang = parts[0]
        topic = parts[1].replace("_", " ").title()
        
        gt_path = os.path.join(GT_DIR, f"{lang_topic}.txt")
        if os.path.exists(gt_path):
            with open(gt_path, "r", encoding="utf-8") as g:
                text = g.read().strip()
            rows.append({
                "filename": f,
                "language": lang,
                "topic": topic,
                "text": text
            })
    
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=["filename", "language", "topic", "text"])
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Consolidated {len(rows)} samples into {OUTPUT_CSV}")

if __name__ == "__main__":
    consolidate()
