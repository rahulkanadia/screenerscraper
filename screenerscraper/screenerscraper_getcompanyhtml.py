import os
import requests
import time
import random
import csv
import shutil
from datetime import datetime

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def run_html_scraper(file_path, folder_path, folder_action):
    print("\n--- Starting HTML Scraper ---")
    if not os.path.exists(file_path): return print(f"File '{file_path}' does not exist.")
    
    urls = []
    with open(file_path, 'r') as file:
        if file_path.endswith('.txt'): urls = [line.strip() for line in file if line.strip()]
        else:
            reader = csv.reader(file)
            next(reader, None)
            urls = [row[0] for row in reader if row]

    if not os.path.exists(folder_path): os.makedirs(folder_path)
    elif folder_action == '1':
        for filename in os.listdir(folder_path):
            p = os.path.join(folder_path, filename)
            os.unlink(p) if os.path.isfile(p) else shutil.rmtree(p)

    existing = set(os.listdir(folder_path)) if folder_action == '3' else set()
    results_log, failed = [], []

    for idx, url in enumerate(urls):
        print(f"[{idx+1}/{len(urls)}] Fetching {url}...")
        company = url.split("/company/")[1].split('/')[0] if "/company/" in url else "unknown"
        counter = 1
        while f"{company}.html" in existing:
            counter += 1
            company = f"{company.split('_')[0]}_{counter}"
            
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                with open(os.path.join(folder_path, f"{company}.html"), 'w', encoding='utf-8') as f:
                    f.write(res.text)
                results_log.append((url, "SUCCESS"))
            else: raise Exception("Bad Status")
        except:
            results_log.append((url, "FAILED"))
            failed.append(url)

        if (idx + 1) % 4 == 0 and (idx + 1) < len(urls):
            time.sleep(random.uniform(2, 5))

    log_path = os.path.join(os.path.dirname(file_path), f"screenerlinks-{datetime.now().strftime('%Y-%m-%d')}.txt")
    with open(log_path, 'w') as f:
        for u, s in results_log: f.write(f"{u} - {s}\n")
        f.write("\n--- Failed Links ---\n")
        for u in failed: f.write(f"{u}\n")
    print(f"Complete! Log saved to '{log_path}'")