import requests
import json
import os

# Configuration
SPARQL_URL = "https://query.wikidata.org/sparql"
TARGET_LANGS = ["en", "zh", "ja", "ar", "vi"]
MAPPING_FILE = "data/parallel_urls_mapping.json"
LIMIT = 40  # Target more to allow for filtering errors

SPARQL_QUERY = """
SELECT DISTINCT ?item ?itemLabel ?en_wiki ?zh_wiki ?ja_wiki ?ar_wiki ?vi_wiki
WHERE {
  ?en_link schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . BIND(STR(?en_link) AS ?en_wiki)
  ?zh_link schema:about ?item ; schema:isPartOf <https://zh.wikipedia.org/> . BIND(STR(?zh_link) AS ?zh_wiki)
  ?ja_link schema:about ?item ; schema:isPartOf <https://ja.wikipedia.org/> . BIND(STR(?ja_link) AS ?ja_wiki)
  ?ar_link schema:about ?item ; schema:isPartOf <https://ar.wikipedia.org/> . BIND(STR(?ar_link) AS ?ar_wiki)
  ?vi_link schema:about ?item ; schema:isPartOf <https://vi.wikipedia.org/> . BIND(STR(?vi_link) AS ?vi_wiki)
  
  # Ensure it is a general topic (instance of any class)
  ?item wdt:P31 ?type .
  
  # Exclude categories/files by requiring a label
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT """ + str(LIMIT)

def discover_topics():
    print(f"Fetching expansion topics from Wikidata...")
    headers = {
        "User-Agent": "DatasetCollector/1.0 (joaopaulo@example.com)",
        "Accept": "application/sparql-results+json"
    }
    
    try:
        response = requests.get(SPARQL_URL, params={'query': SPARQL_QUERY}, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Load existing mapping to avoid duplicates
        if os.path.exists(MAPPING_FILE):
            with open(MAPPING_FILE, "r", encoding="utf-8") as f:
                mapping = json.load(f)
        else:
            mapping = {}
            
        existing_topics = set(mapping.keys())
        new_count = 0
        
        for result in data['results']['bindings']:
            topic_label = result['itemLabel']['value']
            
            # Skip if already in mapping (allowing for slight name differences)
            if topic_label in existing_topics:
                continue
                
            # Construct language entries
            lang_mapping = {
                "en": result['en_wiki']['value'],
                "zh_simp": f"{result['zh_wiki']['value']}?variant=zh-hans",
                "zh_trad": f"{result['zh_wiki']['value']}?variant=zh-hant",
                "ja": result['ja_wiki']['value'],
                "ar": result['ar_wiki']['value'],
                "vi": result['vi_wiki']['value']
            }
            
            mapping[topic_label] = lang_mapping
            new_count += 1
            if new_count >= 25: # Batch limit
                break
                
        # Save updated mapping
        os.makedirs(os.path.dirname(MAPPING_FILE), exist_ok=True)
        with open(MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=4, ensure_ascii=False)
            
        print(f"Successfully added {new_count} new topics to {MAPPING_FILE}")
        
    except Exception as e:
        print(f"Error during topic discovery: {e}")

if __name__ == "__main__":
    discover_topics()
