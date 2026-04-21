import json
import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.firefox import GeckoDriverManager

# Configuration
INPUT_MAPPING = "data/parallel_urls_mapping.json"
OUTPUT_IMG_DIR = "data/raw/parallel_clean"
OUTPUT_GT_DIR = "data/ground_truth/parallel_clean"
TEMP_HTML = "temp_render.html"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            background-color: white;
            color: black;
            font-family: "Helvetica Neue", Helvetica, Arial, "Noto Sans", sans-serif;
            font-size: 28px;
            line-height: 1.6;
            margin: 0;
            padding: 50px;
            width: 900px;
        }}
        a {{ color: black; text-decoration: none; }} /* Clean links */
        sup, .mw-empty-elt {{ display: none; }}
        ruby {{ font-size: 0.8em; }}
    </style>
</head>
<body>
    <div class="content">
        {content}
    </div>
</body>
</html>
"""

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    service = FirefoxService(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    return driver

def get_clean_content(url, lang):
    headers = {"User-Agent": "DatasetCollector/1.0 (joaopaulo@example.com)"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Decompose absolute noise
        for noise in soup.select(".infobox, .sidebar, .hatnote, .navbox, .noprint, .ambox, .metadata, .tmulti, .thumb, .reflist"):
            noise.decompose()
            
        # Target all paragraphs in the document
        all_p = soup.find_all("p")
        
        paragraphs = []
        for p in all_p:
            text = p.get_text().strip()
            # If the paragraph has substantial text, it's a candidate
            if len(text) > 30:
                # Remove citations
                for sup in p.find_all("sup"):
                    sup.decompose()
                paragraphs.append(p)
                if len(paragraphs) >= 2:
                    break
        
        if not paragraphs:
            print(f"    Error: Truly no content for {url}")
            return None, None
            
        html_parts = [str(p) for p in paragraphs]
        text_parts = [p.get_text().strip() for p in paragraphs]
            
        return "".join(html_parts), "\n".join(text_parts)
        
        if not paragraphs:
            return None, None
            
        # Clean HTML for rendering
        html_parts = []
        text_parts = []
        for p in paragraphs:
            # Remove citations
            for sup in p.find_all("sup"):
                sup.decompose()
            html_parts.append(str(p))
            text_parts.append(p.get_text().strip())
            
        return "".join(html_parts), "\n".join(text_parts)
    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return None, None

def render_all():
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
                img_name = f"{lang}_{safe_topic}.png"
                gt_name = f"{lang}_{safe_topic}.txt"
                img_path = os.path.join(OUTPUT_IMG_DIR, img_name)
                gt_path = os.path.join(OUTPUT_GT_DIR, gt_name)
                
                print(f"  Rendering {lang}: {url}...")
                
                html_content, clean_text = get_clean_content(url, lang)
                if not html_content:
                    print(f"    Warning: No content found for {lang}_{safe_topic}")
                    continue
                
                # Create temp HTML file
                full_html = HTML_TEMPLATE.format(lang=lang, content=html_content)
                with open(TEMP_HTML, "w", encoding="utf-8") as f:
                    f.write(full_html)
                
                # Render
                driver.get(f"file://{os.path.abspath(TEMP_HTML)}")
                time.sleep(2) # Wait for fonts
                
                # Resize window to fit content
                height = driver.execute_script("return document.body.scrollHeight")
                driver.set_window_size(1000, height + 100)
                
                # Screenshot
                body = driver.find_element(By.TAG_NAME, "body")
                body.screenshot(img_path)
                
                # Save Ground Truth
                with open(gt_path, "w", encoding="utf-8") as f:
                    f.write(clean_text)
                    
                print(f"    Saved: {img_name}")
                
    finally:
        driver.quit()
        if os.path.exists(TEMP_HTML):
            os.remove(TEMP_HTML)

if __name__ == "__main__":
    render_all()
