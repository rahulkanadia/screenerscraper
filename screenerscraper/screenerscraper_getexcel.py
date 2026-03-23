import os
import requests
import time
import random
import csv

def extract_id(url):
    try: return url.split("/company/")[1].strip('/').split('/')[0]
    except: return None

def run_excel_scraper(file_path, folder_path, session_cookie, batch_size=25, pause_mins=5):
    print("\n--- Starting Excel Batch Downloader ---")
    urls = []
    with open(file_path, 'r', encoding='utf-8') as file:
        if file_path.endswith('.txt'): urls = [line.strip() for line in file if line.strip()]
        else:
            reader = csv.reader(file)
            next(reader, None)
            urls = [row[0] for row in reader if row]

    os.makedirs(folder_path, exist_ok=True)
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.screener.in/'}
    cookies = {'sessionid': session_cookie}

    # Safe Loop instead of Recursion
    while True:
        existing = set(os.listdir(folder_path))
        pending = [(u, extract_id(u)) for u in urls if extract_id(u) and f"{extract_id(u)}.xlsx" not in existing]
        
        if not pending: 
            print("Success: All companies downloaded!")
            break

        batch = pending[:batch_size]
        print(f"Found {len(pending)} pending. Processing batch of {len(batch)}...")

        dl, failed = 0, 0
        for url, cid in batch:
            try:
                res = requests.get(f"https://www.screener.in/excel/{cid}/", headers=headers, cookies=cookies, timeout=15)
                if res.status_code == 200:
                    with open(os.path.join(folder_path, f"{cid}.xlsx"), 'wb') as f: f.write(res.content)
                    dl += 1
                    print(f"Grabbed: {cid}")
                    time.sleep(random.uniform(2.5, 5.0))
                else:
                    failed += 1
                    time.sleep(1.5)
            except:
                failed += 1
                time.sleep(2.0)

        print(f"\nBatch Summary: {dl} downloaded, {failed} failed.")

        if len(pending) > batch_size:
            print(f"Pausing for {pause_mins} minutes to avoid rate limits...")
            for _ in range(pause_mins * 60):
                time.sleep(1) # Allows clean interruption
        else:
            print("All batches complete!")
            break