import json
import os
import time
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.firefox import GeckoDriverManager

# Configuration
INPUT_MAPPING = "data/parallel_urls_mapping.json"
OUTPUT_IMG_DIR = "data/raw/parallel"
OUTPUT_GT_DIR = "data/ground_truth/parallel"

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.set_preference("intl.accept_languages", "en-US, en")
    
    # Use webdriver_manager to handle geckodriver
    service = FirefoxService(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    driver.set_window_size(1280, 1024)
    return driver

def harvest():
    if not os.path.exists(INPUT_MAPPING):
        print(f"Error: {INPUT_MAPPING} not found.")
        return

    with open(INPUT_MAPPING, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)
    os.makedirs(OUTPUT_GT_DIR, exist_ok=True)

    driver = setup_driver()
    
    try:
        for topic, langs in mapping.items():
            print(f"\nProcessing Topic: {topic}")
            for lang, url in langs.items():
                safe_topic = topic.replace(" ", "_").lower()
                img_path = os.path.join(OUTPUT_IMG_DIR, f"{lang}_{safe_topic}.png")
                gt_path = os.path.join(OUTPUT_GT_DIR, f"{lang}_{safe_topic}.txt")
                
                print(f"  Harvesting {lang}: {url}...")
                try:
                    driver.get(url)
                    # Set zoom level to 2.0 for higher DPI screenshots (better for OCR)
                    driver.execute_script("document.body.style.zoom='200%'")
                    time.sleep(5) # Wait for rendering and zoom
                    
                    # Target paragraphs anywhere inside the main content area
                    # Filter out paragraphs that are likely not the lead text
                    all_p = driver.find_elements(By.CSS_SELECTOR, ".mw-parser-output > p, .mw-parser-output > div > p")
                    paragraphs = [p for p in all_p if len(p.text.strip()) > 40]
                    
                    if not paragraphs:
                        # Fallback for some languages where the layout is different
                        all_p = driver.find_elements(By.TAG_NAME, "p")
                        paragraphs = [p for p in all_p if len(p.text.strip()) > 40]

                    if not paragraphs:
                        print(f"    Warning: No paragraphs found for {lang}_{safe_topic}")
                        continue
                        
                    # Target the first 2 meaningful paragraphs
                    target_paragraphs = paragraphs[:2]
                    full_text = "\n".join([p.text for p in target_paragraphs])
                    with open(gt_path, "w", encoding="utf-8") as f:
                        f.write(full_text)
                    
                    # Screenshot of the first meaningful paragraph
                    target_paragraphs[0].screenshot(img_path)
                    print(f"    Saved: {img_path}")
                    
                except Exception as e:
                    print(f"    Error harvesting {lang}_{safe_topic}: {e}")
                    
    finally:
        driver.quit()

if __name__ == "__main__":
    harvest()
