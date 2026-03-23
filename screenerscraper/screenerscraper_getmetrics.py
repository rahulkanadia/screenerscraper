# --- screenerscraper/screenerscraper_getmetrics.py ---

import os
import json
import re
from bs4 import BeautifulSoup

def clean_text(text):
    clean = text.replace('+', '').replace(',', '').strip()
    return re.sub(r'\s+', ' ', clean)

def generate_metrics_json(html_dir, out_path):
    print("\n--- Scanning HTML for Unique Financial Metrics ---")
    metrics_set = set()
    metrics_output = []
    EXCLUDED_SECTIONS = ["Peers", "Shareholding Pattern", "Documents", "Recent Announcements", "About"]

    html_files = [f for f in os.listdir(html_dir) if f.endswith('.html')]
    if not html_files:
        return False, "Error: No HTML files found in the directory."

    for filename in html_files:
        filepath = os.path.join(html_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            
        # 1. TOP RATIOS
        top_ratios = soup.find('ul', id='top-ratios')
        if top_ratios:
            for li in top_ratios.find_all('li'):
                name_span = li.find('span', class_='name')
                if name_span:
                    metric_name = clean_text(name_span.text)
                    identifier = f"Top Info||{metric_name}"
                    if identifier not in metrics_set:
                        metrics_set.add(identifier)
                        metrics_output.append({"Section": "Top Info", "Metric": metric_name, "Source": "HTML", "Active": True})

        # 2. STANDARD TABLES
        for sec in soup.find_all('section'):
            h2 = sec.find('h2')
            if not h2: continue
            section_name = clean_text(h2.text)
            if section_name in EXCLUDED_SECTIONS: continue

            table = sec.find('table', class_='data-table')
            if not table or not table.find('tbody'): continue

            for tr in table.find('tbody').find_all('tr'):
                row_name_td = tr.find('td', class_='text')
                if row_name_td:
                    for unwanted in row_name_td.find_all(['button', 'span', 'a']):
                        unwanted.decompose() 
                    metric_name = clean_text(row_name_td.get_text(separator=' ', strip=True))
                    if metric_name:
                        identifier = f"{section_name}||{metric_name}"
                        if identifier not in metrics_set:
                            metrics_set.add(identifier)
                            metrics_output.append({"Section": section_name, "Metric": metric_name, "Source": "HTML", "Active": True})

        # 3. GROWTH & CAGR TABLES (Ranges)
        for range_table in soup.find_all('table', class_='ranges-table'):
            th = range_table.find('th')
            if not th: continue
            section_name = clean_text(th.text)
            for tr in range_table.find_all('tr'):
                cols = tr.find_all('td')
                if len(cols) == 2:
                    metric_name = clean_text(cols[0].text)
                    identifier = f"{section_name}||{metric_name}"
                    if identifier not in metrics_set:
                        metrics_set.add(identifier)
                        metrics_output.append({"Section": section_name, "Metric": metric_name, "Source": "HTML", "Active": True})

    metrics_output = sorted(metrics_output, key=lambda x: (x['Section'], x['Metric']))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(metrics_output, f, indent=4)

    return True, f"Success: Built metrics.json with {len(metrics_output)} exact metrics."
