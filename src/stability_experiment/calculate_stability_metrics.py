import os
import csv
import glob
import difflib
import statistics
from collections import defaultdict

def calculate_similarity(text1, text2):
    return difflib.SequenceMatcher(None, text1, text2).ratio()

def generate_html_report(stats, output_path):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LLM OCR Stability Experiment</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background: #f4f7f6; color: #333; }
            h1, h2 { color: #2c3e50; }
            .container { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            table { border-collapse: collapse; width: 100%; margin: 20px 0; background: white; font-size: 0.9em; }
            th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: center; }
            th { background-color: #34495e; color: white; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            .highlight { font-weight: bold; }
            .good { background-color: #d4edda; color: #155724; }
            .bad { background-color: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>LLM OCR Stability Experiment</h1>
            <p>100 rounds of inference per image per model to test resilience and consistency.</p>
    """
    
    images = sorted(list(set(img for model in stats for img in stats[model])))
    models = sorted(list(stats.keys()))
    
    for img in images:
        html += f"<h2>Results for {img}</h2>"
        html += """
        <table>
            <thead>
                <tr>
                    <th>Model</th>
                    <th>Mean Char Length</th>
                    <th>SD Char Length</th>
                    <th>Mean Similarity</th>
                    <th>SD Similarity</th>
                    <th>Mean Error Rate</th>
                    <th>SD Error Rate</th>
                </tr>
            </thead>
            <tbody>
        """
        for model in models:
            if img in stats[model]:
                s = stats[model][img]
                mean_sim = s['mean_sim']
                sim_class = "good" if mean_sim > 0.9 else ("bad" if mean_sim < 0.5 else "")
                html += f"""
                <tr>
                    <td class="highlight">{model}</td>
                    <td>{s['mean_len']:.1f}</td>
                    <td>{s['sd_len']:.2f}</td>
                    <td class="{sim_class}">{s['mean_sim']:.4f}</td>
                    <td>{s['sd_sim']:.4f}</td>
                    <td>{s['mean_err']:.4f}</td>
                    <td>{s['sd_err']:.4f}</td>
                </tr>
                """
        html += "</tbody></table>"
        
    html += """
        </div>
    </body>
    </html>
    """
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML report generated at {output_path}")

def main():
    gt_file = "data/ground_truth/raw2/raw2_manual_ocr_ground_truth.csv"
    output_dirs = [
        "data/results/stability_experiment/hf_outputs",
        "data/results/stability_experiment/ollama_outputs"
    ]
    report_csv = "data/results/stability_experiment/stability_metrics.csv"
    report_html = "data/results/stability_experiment/stability_report.html"
    
    ground_truth = {}
    with open(gt_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ground_truth[row['filename']] = row['text']

    raw_data = []
    
    print("Parsing text files and calculating metrics...")
    for base_dir in output_dirs:
        if not os.path.exists(base_dir):
            continue
            
        for model_name in os.listdir(base_dir):
            model_dir = os.path.join(base_dir, model_name)
            if not os.path.isdir(model_dir):
                continue
                
            for img_name in ground_truth:
                base_img_name = os.path.splitext(img_name)[0]
                files = glob.glob(os.path.join(model_dir, f"{base_img_name}_round_*.txt"))
                
                gt_text = ground_truth[img_name]
                
                for f in files:
                    round_num = f.split("_round_")[-1].replace(".txt", "")
                    with open(f, "r", encoding="utf-8") as tf:
                        pred_text = tf.read().strip()
                        
                    sim = calculate_similarity(gt_text, pred_text)
                    err = 1.0 - sim
                    length = len(pred_text)
                    
                    raw_data.append({
                        "model": model_name,
                        "image": img_name,
                        "round": int(round_num),
                        "length": length,
                        "similarity": sim,
                        "error_rate": err
                    })

    # Save raw data CSV
    if raw_data:
        keys = raw_data[0].keys()
        with open(report_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(raw_data)
        print(f"Raw metrics saved to {report_csv}")

    # Aggregate statistics
    aggregated = defaultdict(lambda: defaultdict(list))
    for row in raw_data:
        aggregated[row['model']][row['image']].append(row)
        
    stats = defaultdict(dict)
    
    for model in aggregated:
        for img in aggregated[model]:
            rows = aggregated[model][img]
            lengths = [r['length'] for r in rows]
            sims = [r['similarity'] for r in rows]
            errs = [r['error_rate'] for r in rows]
            
            stats[model][img] = {
                'mean_len': statistics.mean(lengths),
                'sd_len': statistics.stdev(lengths) if len(lengths) > 1 else 0.0,
                'mean_sim': statistics.mean(sims),
                'sd_sim': statistics.stdev(sims) if len(sims) > 1 else 0.0,
                'mean_err': statistics.mean(errs),
                'sd_err': statistics.stdev(errs) if len(errs) > 1 else 0.0,
            }
            
    generate_html_report(stats, report_html)

if __name__ == "__main__":
    main()
