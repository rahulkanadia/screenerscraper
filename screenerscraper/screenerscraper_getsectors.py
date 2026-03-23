import os
import json
from bs4 import BeautifulSoup

def generate_sectors_json(html_dir, out_path):
    print("\n--- Scanning HTML for Sector Classifications ---")
    sectors_set = set()
    sectors_output = []
    
    html_files = [f for f in os.listdir(html_dir) if f.endswith('.html')]
    if not html_files:
        return False, "Error: No HTML files found in the directory."

    for filename in html_files:
        filepath = os.path.join(html_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            
        peers = soup.find('section', id='peers')
        if peers:
            b_sec = peers.find('a', title='Broad Sector')
            sec = peers.find('a', title='Sector')
            b_ind = peers.find('a', title='Broad Industry')
            ind = peers.find('a', title='Industry')
            
            b_sec_t = b_sec.text.strip() if b_sec else "Unknown"
            sec_t = sec.text.strip() if sec else "Unknown"
            b_ind_t = b_ind.text.strip() if b_ind else "Unknown"
            ind_t = ind.text.strip() if ind else "Unknown"
            
            # Use Industry as the unique identifier key
            if ind_t != "Unknown":
                identifier = f"{b_sec_t}|{sec_t}|{b_ind_t}|{ind_t}"
                if identifier not in sectors_set:
                    sectors_set.add(identifier)
                    sectors_output.append({
                        "Broad Sector": b_sec_t,
                        "Sector": sec_t,
                        "Broad Industry": b_ind_t,
                        "Industry": ind_t,
                        "Active": True
                    })

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(sectors_output, f, indent=4)

    return True, f"Success: Built sectors.json with {len(sectors_output)} industries."