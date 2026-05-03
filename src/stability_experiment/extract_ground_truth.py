import csv
import os

def extract_ground_truth():
    input_txt = "data/raw2/New_OCR_extracted.txt"
    output_csv = "data/ground_truth/raw2/raw2_manual_ocr_ground_truth.csv"
    
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    with open(input_txt, 'r', encoding='utf-8') as f:
        content = f.read()

    # The docx was dumped to text with clear section headers like "2. Mainland Chinese"
    # We will manually split and assign them based on the visual structure of the document
    sections = {}
    
    # Very manual extraction based on the known structure of New_OCR_extracted.txt
    
    # 1. TRADITIONAL CHINESE – HONGKONG
    hk_start = content.find("TRADITIONAL CHINESE – HONGKONG")
    hk_end = content.find("2. Mainland Chinese")
    if hk_start != -1 and hk_end != -1:
        hk_text = content[hk_start:hk_end]
        # Clean metadata (URL, Title, etc.) and keep only the body
        body_start = hk_text.find("科學（英語：science；")
        if body_start != -1:
            sections["Science_HK_Chinese.png"] = hk_text[body_start:].strip()

    # 2. Mainland Chinese
    zh_start = hk_end
    zh_end = content.find("3. Japanese")
    if zh_start != -1 and zh_end != -1:
        zh_text = content[zh_start:zh_end]
        body_start = zh_text.find("科学（英语：science；")
        if body_start != -1:
            sections["Science_ZH_Chinese.png"] = zh_text[body_start:].strip()

    # 3. Japanese
    ja_start = zh_end
    ja_end = content.find("4. English")
    if ja_start != -1 and ja_end != -1:
        ja_text = content[ja_start:ja_end]
        body_start = ja_text.find("科学（かがく、英")
        if body_start != -1:
            sections["Science_Japanese.png"] = ja_text[body_start:].strip()

    # 4. English
    en_start = ja_end
    en_end = content.find("5. H HongKong Chinese")
    if en_start != -1:
        en_text = content[en_start:en_end] if en_end != -1 else content[en_start:]
        body_start = en_text.find("Science")
        # Find the second occurrence of Science (skipping the title)
        body_start = en_text.find("Science", body_start + 10)
        # Find the actual start of the paragraph
        body_start = en_text.find("is a systematic discipline")
        if body_start != -1:
            # Go back to include "Science "
            body_start -= 8
            sections["Science_English.png"] = en_text[body_start:].strip()

    # Save to CSV
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "text"])
        writer.writeheader()
        for filename, text in sections.items():
            writer.writerow({"filename": filename, "text": text})

    print(f"Extracted {len(sections)} ground truth entries.")
    for k, v in sections.items():
        print(f"  {k}: {len(v)} characters")
    print(f"Saved to {output_csv}")

if __name__ == "__main__":
    extract_ground_truth()
