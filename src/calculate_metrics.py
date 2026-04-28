import os
import csv
import json
import glob

def edit_distance(s1, s2):
    """Calculates the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return edit_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def calculate_cer(reference, hypothesis):
    """Calculates Character Error Rate (CER)."""
    if not reference:
        return 1.0 if hypothesis else 0.0
    
    distance = edit_distance(reference, hypothesis)
    return min(distance / len(reference), 1.0)

def process_results():
    input_dir = "data/results/raw_predictions"
    output_file = "data/results/processed_metrics.csv"
    
    csv_files = glob.glob(os.path.join(input_dir, "*.csv"))
    
    all_metrics = []
    
    print(f"Found {len(csv_files)} result files. Calculating metrics...")
    
    for csv_file in csv_files:
        model_name = os.path.basename(csv_file).replace("_results.csv", "")
        print(f"  Processing {model_name}...")
        
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ref = row['ground_truth']
                hyp = row['prediction']
                
                cer = calculate_cer(ref, hyp)
                
                all_metrics.append({
                    "model": model_name,
                    "filename": row['filename'],
                    "language": row['language'],
                    "topic": row['topic'],
                    "cer": cer
                })
                
    # Save processed metrics
    if all_metrics:
        keys = all_metrics[0].keys()
        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_metrics)
        print(f"Metrics saved to {output_file}")
    else:
        print("No metrics to calculate.")

if __name__ == "__main__":
    process_results()
