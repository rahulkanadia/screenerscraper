# --- screenerscraper/screenerscraper.py ---

import os
import csv
import re
from bs4 import BeautifulSoup
from datetime import datetime

def clean_text(text):
    """Cleans text and converts % to pure decimals."""
    clean = text.replace('+', '').replace(',', '').strip()
    clean = re.sub(r'\s+', ' ', clean)
    
    if clean.endswith('%') and len(clean) > 1:
        try:
            num = float(clean[:-1])
            return f"{num / 100:.4f}".rstrip('0').rstrip('.')
        except ValueError:
            return clean
    elif clean == '%':
        return ""
    return clean

def parse_html(filepath):
    with open(filepath, 'r', encoding='utf-8') as f: 
        soup = BeautifulSoup(f, 'html.parser')
        
    data = {'static': {
        'Company Name': 'Unknown', 'BSE Code': 'N/A', 'NSE Symbol': 'N/A',
        'Broad Sector': 'Unknown', 'Sector': 'Unknown', 'Broad Industry': 'Unknown', 'Industry': 'Unknown'
    }, 'financials': {}}

    h1 = soup.find('h1')
    if h1: data['static']['Company Name'] = clean_text(h1.text)
    for link in soup.find_all('a', href=True):
        if 'bseindia.com' in link['href']:
            m = re.search(r'/(\d{6})/?$', link['href'])
            if m: data['static']['BSE Code'] = m.group(1)
        elif 'nseindia.com' in link['href']:
            m = re.search(r'symbol=([^&]+)', link['href'])
            if m: data['static']['NSE Symbol'] = m.group(1)

    peers = soup.find('section', id='peers')
    if peers:
        for tag in ['Broad Sector', 'Sector', 'Broad Industry', 'Industry']:
            t = peers.find('a', title=tag)
            if t: data['static'][tag] = clean_text(t.text)

    # 1. Top Info
    data['financials']['Top Info'] = {}
    top_ratios = soup.find('ul', id='top-ratios')
    if top_ratios:
        for li in top_ratios.find_all('li'):
            name = li.find('span', class_='name')
            value = li.find('span', class_='number')
            if name and value:
                data['financials']['Top Info'][clean_text(name.text)] = {"Static": clean_text(value.text)}

    # 2. Standard Tables
    for sec in soup.find_all('section'):
        h2 = sec.find('h2')
        table = sec.find('table', class_='data-table')
        if not h2 or not table or not table.find('thead'): continue
        
        section_name = clean_text(h2.text)
        data['financials'][section_name] = {}
        
        col_to_period = {}
        for idx, th in enumerate(table.find('thead').find_all('th')):
            th_text = th.text.strip()
            if "TTM" in th_text: col_to_period[idx] = "TTM"
            else:
                m = re.search(r'([A-Z][a-z]{2}\s\d{4})', th_text)
                if m: col_to_period[idx] = m.group(1)

        tbody = table.find('tbody')
        if tbody:
            for row in tbody.find_all('tr'):
                cols = row.find_all('td')
                if not cols: continue
                
                row_name_td = cols[0]
                for unwanted in row_name_td.find_all(['button', 'span', 'a']):
                    unwanted.decompose()
                    
                metric_name = clean_text(row_name_td.get_text(separator=' ', strip=True))
                if not metric_name: continue
                
                data['financials'][section_name][metric_name] = {}
                for idx, col in enumerate(cols):
                    if idx in col_to_period:
                        period = col_to_period[idx]
                        data['financials'][section_name][metric_name][period] = clean_text(col.text)

    # 3. Growth & CAGR Tables
    for range_table in soup.find_all('table', class_='ranges-table'):
        th = range_table.find('th')
        if not th: continue
        section_name = clean_text(th.text)
        data['financials'][section_name] = {}
        for tr in range_table.find_all('tr'):
            cols = tr.find_all('td')
            if len(cols) == 2:
                metric_name = clean_text(cols[0].text)
                val = clean_text(cols[1].text)
                data['financials'][section_name][metric_name] = {"Static": val}

    return data

def get_target_periods(active_years, active_qtrs, inc_ttm):
    periods = ["TTM"] if inc_ttm else []
    active_years.sort(reverse=True)
    for y in active_years:
        for q in ["Dec", "Sep", "Jun", "Mar"]:
            if q in active_qtrs: periods.append(f"{q} {y}")
    return periods

def run_parser(html_folder, active_years, active_qtrs, inc_ttm, active_metrics, active_sectors, progress_bar=None, status_text=None):
    files = [os.path.join(html_folder, f) for f in os.listdir(html_folder) if f.endswith('.html')]
    if not files: 
        if status_text: status_text.error("No HTML files found.")
        return

    total_files = len(files)
    target_periods = get_target_periods(active_years, active_qtrs, inc_ttm)
    
    header = [
        "Broad Sector", "Sector", "Broad Industry", "Industry", 
        "Company Name", "BSE Code", "NSE Symbol", "Section", "Metric"
    ] + target_periods

    out_file = f"screenerscraped-{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
    
    with open(out_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        
        for idx, fp in enumerate(files):
            d = parse_html(fp)
            stat = d['static']
            
            if progress_bar: progress_bar.progress((idx + 1) / total_files)
            if status_text: status_text.text(f"Processing ({idx + 1}/{total_files}): {stat['Company Name']}...")
            
            if active_sectors and stat['Industry'] not in active_sectors: continue
                
            base_info = [stat['Broad Sector'], stat['Sector'], stat['Broad Industry'], stat['Industry'], stat['Company Name'], stat['BSE Code'], stat['NSE Symbol']]

            for metric in active_metrics:
                sec_name = metric.get('Section')
                met_name = metric.get('Metric')
                row = base_info.copy() + [sec_name, met_name]
                
                periods_data = d['financials'].get(sec_name, {}).get(met_name, {})
                
                # Logic to handle both Time-Series and Static (CAGR/Top Info) data
                if "Static" in periods_data:
                    row.append(periods_data["Static"])
                    row.extend([""] * (len(target_periods) - 1)) # Pad the rest of the periods with blanks
                else:
                    for p in target_periods:
                        row.append(periods_data.get(p, ""))
                    
                writer.writerow(row)

def run_shareholding_parser(html_folder, active_years, active_qtrs, active_sectors, progress_bar=None, status_text=None):
    files = [os.path.join(html_folder, f) for f in os.listdir(html_folder) if f.endswith('.html')]
    if not files: return
    
    total_files = len(files)
    target_periods = get_target_periods(active_years, active_qtrs, False) 
    header = ["Broad Sector", "Sector", "Broad Industry", "Industry", "Company Name", "BSE Code", "NSE Symbol", "Metric"] + target_periods
    out_file = f"shareholding-{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
    
    with open(out_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for idx, fp in enumerate(files):
            d = parse_html(fp) 
            stat = d['static']
            
            if progress_bar: progress_bar.progress((idx + 1) / total_files)
            if status_text: status_text.text(f"Processing ({idx + 1}/{total_files}): {stat['Company Name']}...")
            if active_sectors and stat['Industry'] not in active_sectors: continue

            base_info = [stat['Broad Sector'], stat['Sector'], stat['Broad Industry'], stat['Industry'], stat['Company Name'], stat['BSE Code'], stat['NSE Symbol']]
            if 'Shareholding Pattern' in d['financials']:
                for met_name, periods_data in d['financials']['Shareholding Pattern'].items():
                    row = base_info.copy() + [met_name]
                    for p in target_periods:
                        row.append(periods_data.get(p, ""))
                    writer.writerow(row)