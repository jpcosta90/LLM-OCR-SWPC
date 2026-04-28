import csv
import os
from collections import defaultdict

def generate_report():
    input_file = "data/results/processed_metrics.csv"
    output_report = "reports/benchmark_report.html"
    os.makedirs("reports", exist_ok=True)
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run calculate_metrics.py first.")
        return

    # Data structures
    # model -> language -> [cer1, cer2, ...]
    data = defaultdict(lambda: defaultdict(list))
    languages = set()
    models = set()
    
    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            model = row['model']
            lang = row['language']
            cer = float(row['cer'])
            data[model][lang].append(cer)
            languages.add(lang)
            models.add(model)
            
    sorted_langs = sorted(list(languages))
    sorted_models = sorted(list(models))
    
    # Calculate Averages
    averages = defaultdict(dict)
    model_totals = defaultdict(list)
    
    for model in sorted_models:
        for lang in sorted_langs:
            vals = data[model].get(lang, [])
            if vals:
                avg = sum(vals) / len(vals)
                averages[model][lang] = avg
                model_totals[model].extend(vals)
            else:
                averages[model][lang] = None
    
    # Generate HTML
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Impossible Triangle: Multimodal OCR Benchmark</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background: #f4f7f6; color: #333; }
            h1, h2 { color: #2c3e50; }
            .container { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            table { border-collapse: collapse; width: 100%; margin: 20px 0; background: white; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: center; }
            th { background-color: #34495e; color: white; }
            .heatmap-cell { font-weight: bold; }
            .low-error { background-color: #d4edda; color: #155724; }
            .mid-error { background-color: #fff3cd; color: #856404; }
            .high-error { background-color: #f8d7da; color: #721c24; }
            .summary-box { display: flex; gap: 20px; margin-bottom: 30px; }
            .stat-card { flex: 1; padding: 20px; border-radius: 8px; color: white; text-align: center; }
            .best-model { background: #27ae60; }
            .avg-cer { background: #2980b9; }
            .footer { margin-top: 50px; font-size: 0.9em; color: #7f8c8d; border-top: 1px solid #ddd; padding-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Impossible Triangle: OCR Benchmark Report</h1>
            <p>Comparative analysis of Multimodal LLMs across 6 languages and 27 topics (162 total samples).</p>
            
            <div class="summary-box">
    """
    
    # Calculate global best
    best_overall_model = ""
    best_overall_cer = 1.0
    for model, vals in model_totals.items():
        avg = sum(vals) / len(vals)
        if avg < best_overall_cer:
            best_overall_cer = avg
            best_overall_model = model
            
    html += f"""
                <div class="stat-card best-model">
                    <h3>🏆 Best Overall Model</h3>
                    <div style="font-size: 1.5em; font-weight: bold;">{best_overall_model}</div>
                    <p>CER: {best_overall_cer:.2%}</p>
                </div>
                <div class="stat-card avg-cer">
                    <h3>📊 Total Samples</h3>
                    <div style="font-size: 1.5em; font-weight: bold;">{len(models) * 162}</div>
                    <p>Processed across all families</p>
                </div>
            </div>
            
            <h2>Language x Model Performance (CER Heatmap)</h2>
            <p>Lower is better. Cells are color-coded based on Character Error Rate.</p>
            <table>
                <thead>
                    <tr>
                        <th>Language / Model</th>
    """
    
    for model in sorted_models:
        html += f"<th>{model}</th>"
    html += "</tr></thead><tbody>"
    
    for lang in sorted_langs:
        html += f"<tr><td style='font-weight:bold; background:#f9f9f9;'>{lang.upper()}</td>"
        for model in sorted_models:
            val = averages[model][lang]
            if val is not None:
                color_class = "low-error" if val < 0.05 else ("mid-error" if val < 0.2 else "high-error")
                html += f"<td class='heatmap-cell {color_class}'>{val:.2%}</td>"
            else:
                html += "<td>N/A</td>"
        html += "</tr>"
        
    html += """
                </tbody>
            </table>
            
            <h2>Detailed Metrics by Model Family</h2>
            <ul>
    """
    
    for model in sorted_models:
        avg = sum(model_totals[model]) / len(model_totals[model])
        html += f"<li><strong>{model}</strong>: Average CER {avg:.2%}</li>"
        
    html += """
            </ul>
            
            <div class="footer">
                Report generated on: """ + str(os.popen("date").read()) + """<br>
                Impossible Triangle Research Pipeline v1.0
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(output_report, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"Report generated successfully at {output_report}")

if __name__ == "__main__":
    generate_report()
