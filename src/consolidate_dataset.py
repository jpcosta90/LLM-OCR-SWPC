import os
import csv
from collections import defaultdict

# Configuration
IMG_DIR = "data/raw/parallel_clean"
GT_DIR = "data/ground_truth/parallel_clean"
OUTPUT_CSV = "data/ground_truth/dataset_mirror_v1.csv"

# The target language set for a perfect parallel matrix
REQUIRED_LANGS = ["en", "ar", "ja", "vi", "zh_simp", "zh_trad"]

def parse_filename(f):
    """
    Correctly splits filenames like:
    zh_simp_earth.png -> (zh_simp, earth)
    en_earth.png      -> (en, earth)
    """
    base = f.replace(".png", "")
    
    if base.startswith("zh_simp_"):
        return "zh_simp", base.replace("zh_simp_", "")
    if base.startswith("zh_trad_"):
        return "zh_trad", base.replace("zh_trad_", "")
    
    # Generic [lang]_[topic]
    parts = base.split("_", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, None

def consolidate():
    files = [f for f in os.listdir(IMG_DIR) if f.endswith(".png")]
    
    # Group rows by topic
    topic_map = defaultdict(list)
    
    for f in files:
        lang, topic_slug = parse_filename(f)
        if not lang or not topic_slug:
            continue
            
        topic_display = topic_slug.replace("_", " ").title()
        
        gt_path = os.path.join(GT_DIR, f"{f.replace('.png', '.txt')}")
        if os.path.exists(gt_path):
            with open(gt_path, "r", encoding="utf-8") as g:
                text = g.read().strip()
            
            topic_map[topic_slug].append({
                "filename": f,
                "language": lang,
                "topic": topic_display,
                "text": text
            })
    
    # Filter for perfect topics only (all 6 languages must exist)
    perfect_rows = []
    complete_topics = 0
    total_topics = len(topic_map)
    
    # Ensure topics are sorted for consistency
    sorted_topics = sorted(topic_map.keys())
    
    for topic in sorted_topics:
        rows = topic_map[topic]
        present_langs = [r["language"] for r in rows]
        
        # Check if all 6 required languages are present
        if all(lang in present_langs for lang in REQUIRED_LANGS):
            # Sort rows by language order for a clean CSV
            rows.sort(key=lambda x: REQUIRED_LANGS.index(x["language"]))
            perfect_rows.extend(rows)
            complete_topics += 1
        else:
            missing = set(REQUIRED_LANGS) - set(present_langs)
            print(f"Skipping incomplete topic: {topic} (Missing: {missing})")
            
    # Write the consolidated CSV
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=["filename", "language", "topic", "text"])
        writer.writeheader()
        writer.writerows(perfect_rows)
        
    print("-" * 30)
    print(f"Total topics found: {total_topics}")
    print(f"Perfect parallel topics kept: {complete_topics}")
    print(f"Total rows in CSV: {len(perfect_rows)}")
    print(f"Final parity check: {len(perfect_rows) / 6} articles per language.")

if __name__ == "__main__":
    consolidate()
