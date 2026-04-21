import requests
import json
import os

# Configuration
QIDS = {
    "Hydrogen Isotopes": "Q466603",
    "Periodic Table": "Q10693",
    "History of Printing": "Q257933",
    "Artificial Intelligence": "Q11660"
}

LANGUAGES = {
    "en": "enwiki",
    "zh_simp": "zhwiki",    # Map to zh-hans variant later
    "zh_trad": "zhwiki",    # Map to zh-hant variant later
    "ja": "jawiki",
    "ar": "arwiki",
    "vi": "viwiki"
}

def get_wikipedia_urls(qid):
    # Wikidata requires a User-Agent header
    headers = {
        "User-Agent": "DatasetCollector/1.0 (joaopaulo@example.com)"
    }
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    try:
        response = requests.get(url, headers=headers, allow_redirects=True)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching {qid}: {e}")
        return {}
    
    entities = data.get("entities", {})
    if not entities:
        return {}
    
    entity = entities.get(qid, {})
    sitelinks = entity.get("sitelinks", {})
    
    mapping = {}
    for lang_key, wiki_key in LANGUAGES.items():
        if wiki_key in sitelinks:
            title = sitelinks[wiki_key]["title"]
            base_url = f"https://{wiki_key[:2]}.wikipedia.org/wiki/{title.replace(' ', '_')}"
            
            # Apply variants for Chinese
            if lang_key == "zh_simp":
                mapping[lang_key] = f"{base_url}?variant=zh-hans"
            elif lang_key == "zh_trad":
                mapping[lang_key] = f"{base_url}?variant=zh-hant"
            else:
                mapping[lang_key] = base_url
                
    return mapping

def main():
    dataset_mapping = {}
    for topic, qid in QIDS.items():
        print(f"Fetching URLs for: {topic} ({qid})...")
        urls = get_wikipedia_urls(qid)
        dataset_mapping[topic] = urls
        
    os.makedirs("data", exist_ok=True)
    with open("data/parallel_urls_mapping.json", "w", encoding="utf-8") as f:
        json.dump(dataset_mapping, f, indent=4, ensure_ascii=False)
    
    print("\nMapping saved to data/parallel_urls_mapping.json")
    for topic, lang_urls in dataset_mapping.items():
        print(f"\n{topic}:")
        for lang, url in lang_urls.items():
            print(f"  {lang}: {url}")

if __name__ == "__main__":
    main()
