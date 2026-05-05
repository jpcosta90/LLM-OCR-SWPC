import csv
import os

def extract_h_novo_ground_truth():
    input_txt = "data/raw2/H_Novo_extracted.txt"
    output_csv = "data/ground_truth/raw2/raw2_manual_ocr_ground_truth.csv"
    
    with open(input_txt, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = {}
    
    # 1) H_ENG
    en_start = content.find("1) H_ENG: TEXT")
    zh_start = content.find("2) H_ZH：TEXT")
    if en_start != -1 and zh_start != -1:
        en_text = content[en_start:zh_start]
        body_start = en_text.find("Isotopes of hydrogen")
        if body_start != -1:
            sections["H_EN.png"] = en_text[body_start:].strip()

    # 2) H_ZH
    jp_start = content.find("3) H_JP：TEXT")
    if zh_start != -1 and jp_start != -1:
        zh_text = content[zh_start:jp_start]
        body_start = zh_text.find("氢的同位素[编辑]")
        if body_start != -1:
            sections["H_ZH.png"] = zh_text[body_start:].strip()

    # 3) H_JP
    hk_start = content.find("4) H_HK ：TEXT")
    if jp_start != -1 and hk_start != -1:
        jp_text = content[jp_start:hk_start]
        body_start = jp_text.find("水素の同位体")
        if body_start != -1:
            sections["H_JP.png"] = jp_text[body_start:].strip()

    # 4) H_HK
    if hk_start != -1:
        hk_text = content[hk_start:]
        body_start = hk_text.find("氫的同位素[编辑]")
        if body_start != -1:
            sections["H_HK.png"] = hk_text[body_start:].strip()

    # Append to existing CSV (avoiding duplicates)
    existing_files = set()
    if os.path.exists(output_csv):
        with open(output_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_files.add(row["filename"])

    appended_count = 0
    with open(output_csv, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "text"])
        # If the file didn't exist, we would write header, but we know it exists.
        for filename, text in sections.items():
            if filename not in existing_files:
                writer.writerow({"filename": filename, "text": text})
                appended_count += 1
                print(f"Appended {filename}: {len(text)} characters")
            else:
                print(f"Skipped {filename} (already exists)")

    print(f"Successfully appended {appended_count} new ground truth entries.")

if __name__ == "__main__":
    extract_h_novo_ground_truth()
