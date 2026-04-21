import requests
import json
import os

# Specific QIDs to ensure full coverage
TOPICS = {
    "Earth": "Q2",
    "Sun": "Q525",
    "Moon": "Q405",
    "Water": "Q283",
    "Oxygen": "Q629",
    "Gold": "Q897",
    "Iron": "Q677",
    "Mathematics": "Q395",
    "Physics": "Q413",
    "Biology": "Q420",
    "Chemistry": "Q2329",
    "Internet": "Q75",
    "Computer": "Q68",
    "Mobile Phone": "Q17517",
    "Electricity": "Q12725",
    "Paper": "Q11472",
    "Wheel": "Q446",
    "Fire": "Q3196",
    "Agriculture": "Q11451",
    "Democracy": "Q7174",
    "Philosophy": "Q5891",
    "Music": "Q638",
    "Art": "Q735",
    "Architecture": "Q12271"
}

TARGET_LANGS = {
    "en": "enwiki",
    "zh": "zhwiki",
    "ja": "jawiki",
    "ar": "arwiki",
    "vi": "viwiki"
}

MAPPING_FILE = "data/parallel_urls_mapping.json"

def fetch_urls():
    print(f"Fetching URLs for {len(TOPICS)} specific topics...")
    
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            mapping = json.load(f)
    else:
        mapping = {}

    for label, qid in TOPICS.items():
        if label in mapping:
            continue
            
        print(f"  Fetching {label} ({qid})...")
        url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={qid}&props=sitelinks&format=json"
        try:
            r = requests.get(url, headers={"User-Agent": "DatasetCollector/1.0"})
            r.raise_for_status()
            data = r.json()
            sitelinks = data.get("entities", {}).get(qid, {}).get("sitelinks", {})
            
            # Check if all langs exist
            if all(lang_key in sitelinks for lang_key in TARGET_LANGS.values()):
                def make_url(lang_code, wiki_key):
                    title = sitelinks[wiki_key]["title"].replace(" ", "_")
                    return f"https://{lang_code}.wikipedia.org/wiki/{title}"

                lang_mapping = {
                    "en": make_url("en", "enwiki"),
                    "zh_simp": f"{make_url('zh', 'zhwiki')}?variant=zh-hans",
                    "zh_trad": f"{make_url('zh', 'zhwiki')}?variant=zh-hant",
                    "ja": make_url("ja", "jawiki"),
                    "ar": make_url("ar", "arwiki"),
                    "vi": make_url("vi", "viwiki")
                }
                mapping[label] = lang_mapping
                print(f"    Added {label}")
            else:
                print(f"    Skipping {label}: Missing some languages")
        except Exception as e:
            print(f"    Error for {label}: {e}")

    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=4, ensure_ascii=False)
    
    print(f"Total topics in mapping: {len(mapping)}")

if __name__ == "__main__":
    fetch_urls()
