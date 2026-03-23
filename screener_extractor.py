import os
import csv
import re
import logging
from bs4 import BeautifulSoup
from datetime import datetime

# --- CONFIGURATION ---
HTML_DIR = "screenerhtml"  # Your main folder with 5000+ files
OUTPUT_CSV = f"screenerscraped-{datetime.now().strftime('%Y-%m-%d')}.csv"
ERROR_LOG = "screener_scraper_errors.log"

# Silently logs errors so your console stays clean
logging.basicConfig(filename=ERROR_LOG, level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_value(text):
    """Strips commas, normalizes spacing, and converts % to pure decimals."""
    if not text: return ""
    clean = text.replace(',', '').strip()
    clean = re.sub(r'\s+', ' ', clean)
    
    if clean.endswith('%') and len(clean) > 1:
        try: return round(float(clean[:-1]) / 100, 4)
        except ValueError: return clean
    elif clean == '%':
        return ""
        
    try: return float(clean)
    except ValueError: return clean

def get_clean_label(td_element):
    """Surgically extracts labels, handling ALL '+' signs and removing hidden tooltips."""
    for tooltip in td_element.find_all(class_='tooltip'):
        tooltip.decompose()
        
    raw_text = td_element.get_text(separator=' ', strip=True)
    # Specifically removes the '+' from 'Sales +', 'Borrowings +', etc.
    clean_text = raw_text.replace('+', '').strip()
    return re.sub(r'\s+', ' ', clean_text)

def parse_screener_html(filepath, audit_tracker):
    """Parses HTML into the strict 'Long' format (Metrics as Rows)."""
    company_rows = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # --- 1. BASE IDENTIFIERS (Repeated on every row) ---
    base_info = {
        'Broad Sector': '', 'Sector': '', 'Broad Industry': '', 'Industry': '',
        'Company Name': 'Unknown', 'BSE Code': '', 'NSE Symbol': ''
    }
    
    h1 = soup.find('h1')
    if h1: base_info['Company Name'] = clean_value(h1.text.replace('+', ''))

    for link in soup.find_all('a', href=True):
        if 'bseindia.com' in link['href']:
            m = re.search(r'/(\d{6})/?$', link['href'])
            if m: base_info['BSE Code'] = m.group(1)
        elif 'nseindia.com' in link['href']:
            m = re.search(r'symbol=([^&]+)', link['href'])
            if m: base_info['NSE Symbol'] = m.group(1)

    peers = soup.find('section', id='peers')
    if peers:
        for tag in ['Broad Sector', 'Sector', 'Broad Industry', 'Industry']:
            t = peers.find('a', title=tag)
            if t: base_info[tag] = clean_value(t.text)

    # --- 2. TOP RATIOS (Static Values) ---
    top_ratios = soup.find('ul', id='top-ratios')
    if top_ratios:
        for li in top_ratios.find_all('li'):
            name = li.find('span', class_='name')
            value = li.find('span', class_='number')
            if name and value:
                row = base_info.copy()
                row.update({
                    'Section': 'Top Info',
                    'Metric': clean_value(name.text),
                    'Static': clean_value(value.text)
                })
                company_rows.append(row)

    # --- 3. STANDARD TABLES (Time Series Data) ---
    sections_to_parse = {
        'quarters': 'Quarterly Results',
        'profit-loss': 'Profit & Loss',
        'balance-sheet': 'Balance Sheet',
        'cash-flow': 'Cash Flows',
        'ratios': 'Ratios',
        'shareholding': 'Shareholding Pattern'
    }

    for section_id, section_name in sections_to_parse.items():
        section = soup.find('section', id=section_id)
        if not section: continue
        
        table = section.find('table', class_='data-table')
        if not table or not table.find('thead') or not table.find('tbody'): continue
        
        audit_tracker[section_id] += 1 

        headers = [clean_value(th.text) for th in table.find('thead').find_all('th')]
        
        for tr in table.find('tbody').find_all('tr'):
            cols = tr.find_all('td')
            if not cols: continue
            
            metric_name = get_clean_label(cols[0])
            if not metric_name or metric_name == 'Raw PDF': continue
            
            row = base_info.copy()
            row.update({'Section': section_name, 'Metric': metric_name})
            
            for idx, col in enumerate(cols[1:], start=1):
                if idx < len(headers):
                    period = headers[idx]
                    row[period] = clean_value(col.text)
            
            company_rows.append(row)

    # --- 4. CAGR & GROWTH TABLES (Static Values) ---
    cagr_found = False
    for range_table in soup.find_all('table', class_='ranges-table'):
        th = range_table.find('th')
        if not th: continue
        
        cagr_found = True
        section_name = clean_value(th.text)
        
        for tr in range_table.find_all('tr'):
            cols = tr.find_all('td')
            if len(cols) >= 2:
                row = base_info.copy()
                row.update({
                    'Section': section_name,
                    'Metric': clean_value(cols[0].text),
                    'Static': clean_value(cols[1].text)
                })
                company_rows.append(row)
                
    if cagr_found: audit_tracker['ranges-table'] += 1

    return company_rows

def sort_period_columns(cols):
    """Sorts dynamic columns chronologically, pushing TTM and Static to the end."""
    months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
    
    def sort_key(col):
        if col == "TTM": return (2099, 0)
        if col == "Static": return (3000, 0)
        m = re.match(r'([A-Z][a-z]{2})\s(\d{4})', str(col))
        if m:
            return (int(m.group(2)), months.get(m.group(1), 0))
        return (0, 0) 
        
    return sorted(cols, key=sort_key)

def main():
    print(f"\n:rocket: Starting Full Extraction from '{HTML_DIR}'...")
    if not os.path.exists(HTML_DIR): return print(f":x: Error: Folder '{HTML_DIR}' not found. Check your path.")

    files = [f for f in os.listdir(HTML_DIR) if f.endswith('.html')]
    if not files: return print(f":x: Error: No HTML files found in '{HTML_DIR}'.")

    all_rows = []
    audit_tracker = {k: 0 for k in ['quarters', 'profit-loss', 'balance-sheet', 'cash-flow', 'ratios', 'shareholding', 'ranges-table']}

    # 1. Parse all files
    for idx, filename in enumerate(files):
        try:
            company_rows = parse_screener_html(os.path.join(HTML_DIR, filename), audit_tracker)
            all_rows.extend(company_rows)
            # Log progress every 250 files to ensure the console proves it isn't frozen
            if (idx + 1) % 250 == 0 or (idx + 1) == len(files):
                print(f":hourglass_flowing_sand: Parsed {idx + 1} / {len(files)} files...")
        except Exception as e:
            logging.error(f"Failed {filename}: {str(e)}")

    # 2. Dynamically build and sort headers
    print("\n:writing_hand: Compiling matrix and sorting chronological headers...")
    period_columns = set()
    base_headers = ["Broad Sector", "Sector", "Broad Industry", "Industry", "Company Name", "BSE Code", "NSE Symbol", "Section", "Metric"]
    
    for row in all_rows:
        for key in row.keys():
            if key not in base_headers:
                period_columns.add(key)

    sorted_periods = sort_period_columns(list(period_columns))
    final_headers = base_headers + sorted_periods

    # 3. Export Data
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=final_headers)
        writer.writeheader()
        writer.writerows(all_rows)

    # 4. Final Audit Report
    print(f"\n:white_check_mark: Success: Massive data matrix saved to '{OUTPUT_CSV}'")
    print("="*40 + "\n:bar_chart: FINAL AUDIT REPORT\n" + "="*40)
    print(f"Files Scanned      : {len(files)}")
    print(f"Total Metric Rows  : {len(all_rows):,}")  # Formats with commas for readability
    print("-" * 40)
    for k, v in audit_tracker.items():
        print(f" - {k.ljust(15)} : {v:,} hits")
    
    if os.path.exists(ERROR_LOG) and os.path.getsize(ERROR_LOG) > 0:
        print("\n:warning: Note: Check 'screener_scraper_errors.log' for any malformed HTML files.")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()