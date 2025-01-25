import os
import random
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

PATHS = {
    'html_dir': r'E:\RnR\Python\company_html',
    'output_dir': r'E:\RnR\Python'
}

TABLE_CLASSES = {
    'main': 'ranges-table',
    'data': 'data-table responsive-text-nowrap'
}

SHEET_CONFIG = {
    'Company_Info': {
        'fields': ['Company Name', 'BSE Tag', 'NSE Tag', 'Market Cap']
    },
    'Main_Metrics': {
        'tables': ['Compounded Sales Growth', 'Compounded Profit Growth',
                  'Stock Price CAGR', 'Return on Equity'],
        'periods': ['10 Years', '5 Years', '3 Years', 'TTM']
    },
    'Quarterly_Results': {
        'table_type': 'data',
        'metrics': ['Sales', 'Expenses', 'Operating Profit', 'OPM %',
                   'Other Income', 'Interest', 'Depreciation', 'Profit before tax',
                   'Tax %', 'Net Profit', 'EPS in Rs']
    },
    'Profit_Loss': {
        'table_type': 'data',
        'section': 'profit-loss',
        'metrics': ['Sales', 'Expenses', 'Operating Profit', 'OPM %',
                   'Other Income', 'Interest', 'Depreciation', 'Profit before tax',
                   'Tax %', 'Net Profit', 'EPS in Rs', 'Dividend Payout %']
    },
    'Balance_Sheet': {
        'table_type': 'data',
        'section': 'balance-sheet',
        'metrics': ['Equity Capital', 'Reserves', 'Borrowings', 'Other Liabilities',
                   'Total Liabilities', 'Fixed Assets', 'CWIP', 'Investments',
                   'Other Assets', 'Total Assets']
    },
    'Cash_Flow': {
        'table_type': 'data',
        'section': 'cash-flow',
        'metrics': ['Cash from Operating Activity', 'Cash from Investing Activity',
                   'Cash from Financing Activity', 'Net Cash Flow']
    },
    'Ratios': {
        'table_type': 'data',
        'section': 'ratios',
        'metrics': ['Debtor Days', 'Inventory Days', 'Days Payable',
                   'Cash Conversion Cycle', 'Working Capital Days', 'ROCE %']
    },
    'Shareholding': {
        'table_type': 'data',
        'section': 'shareholding',
        'metrics': ['Promoters', 'FIIs', 'DIIs', 'Public', 'No. of Shareholders']
    }
}

SHEET_TYPES = {
    'Quarterly_Results': 'Quarterly',
    'Profit_Loss': 'Annual',
    'Balance_Sheet': 'Balance',
    'Cash_Flow': 'Cash_Flow',
    'Ratios': 'Ratios',
    'Shareholding': 'Shareholding'
}

def get_all_files():
    """Get all HTML files from directory"""
    return [f for f in os.listdir(PATHS['html_dir']) if f.endswith('.html')]

def convert_to_full_year(year):
    """Convert 2-digit year to 4-digit year"""
    if len(year) == 2:
        year = int(year)
        return str(2000 + year if year < 50 else 1900 + year)
    return year

def extract_year(column_name):
    """Extract and convert year to 4-digit format"""
    try:
        parts = column_name.split('_')
        if len(parts) < 2:
            return None
        
        date_part = parts[-1]
        if '-' in date_part:
            year = date_part.split('-')[1]
        else:
            year = date_part[-2:]
        
        return convert_to_full_year(year)
    except:
        return None

def extract_stock_tag(soup, exchange='bse'):
    """Extract BSE/NSE tag with enhanced fallback methods"""
    tag = '-'
    
    # Method 1: Direct span search
    span = soup.find('span', string=re.compile(f"{exchange.upper()}:"))
    if span:
        tag = span.text.split(':')[1].strip()
        return tag
    
    # Method 2: Link-based search
    domain = 'bseindia.com' if exchange == 'bse' else 'nseindia.com'
    link = soup.find('a', href=re.compile(domain))
    if link:
        span = link.find('span', {'class': 'ink-700'})
        if span:
            text = span.text.strip()
            if ':' in text:
                tag = text.split(':')[1].strip()
            elif 'BSE - SME:' in text:
                tag = text.split('BSE - SME:')[1].strip()
    
    return tag

def extract_company_info(soup):
    """Extract company details with enhanced tag extraction"""
    try:
        name = soup.find('h1', {'class': 'margin-0'}).text.strip()
        bse = extract_stock_tag(soup, 'bse')
        nse = extract_stock_tag(soup, 'nse')
        
        mcap_div = soup.find('div', {'class': 'font-size-18'})
        mcap = mcap_div.find('span').text.strip() if mcap_div else '-'
        
        return {
            'Company Name': name,
            'BSE Tag': bse,
            'NSE Tag': nse,
            'Market Cap': mcap
        }
    except Exception as e:
        print(f"Company info extraction failed: {str(e)}")
        return None

def extract_main_tables(soup):
    """Extract data from main metric tables"""
    data = {}
    for table_name in SHEET_CONFIG['Main_Metrics']['tables']:
        table = soup.find('th', string=re.compile(table_name))
        if table:
            table = table.find_parent('table')
            rows = table.find_all('tr')[1:5]
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    period = cells[0].text.strip().replace(':', '')
                    value = cells[1].text.strip()
                    data[f"{table_name}_{period}"] = value
    return data

def extract_table_data(soup, sheet_name):
    """Extract data from financial tables"""
    config = SHEET_CONFIG[sheet_name]
    data = {}
    
    section = soup.find('section', {'id': config.get('section', '')})
    table = (section or soup).find('table', {'class': TABLE_CLASSES['data']})
    
    if not table:
        return data

    headers = [th.text.strip() for th in table.find('thead').find_all('th')]
    rows = table.find('tbody').find_all('tr')
    
    for metric in config['metrics']:
        for row in rows:
            cells = row.find_all('td')
            if not cells:
                continue
            
            row_text = cells[0].text.strip()
            if cells[0].find('button'):
                row_text = cells[0].find('button').text.strip().replace('\xa0+', '')
            
            if metric in row_text:
                for i, header in enumerate(headers[1:], 1):
                    try:
                        value = cells[i].text.strip()
                        data[f"{metric}_{header}"] = value
                    except IndexError:
                        data[f"{metric}_{header}"] = '-'
                break
    return data

def organize_sheets_by_year(data):
    """Transform master sheets into year-wise sheets"""
    # Keep static sheets
    final_data = {
        'Company_Info': data.get('Company_Info', []),
        'Main_Metrics': data.get('Main_Metrics', [])
    }
    
    # Company reference data
    companies = {item['Company Name']: item 
                for item in data.get('Company_Info', [])}
    
    # Process each master sheet
    for master_sheet, items in data.items():
        if master_sheet in ['Company_Info', 'Main_Metrics'] or not items:
            continue
            
        sheet_type = SHEET_TYPES.get(master_sheet)
        if not sheet_type:
            continue
        
        # Collect years and metrics
        years_data = {}
        metrics = set()
        
        # First pass: gather all data by year
        for item in items:
            for col, value in item.items():
                if '_' in col:
                    year = extract_year(col)
                    if year:
                        if year not in years_data:
                            years_data[year] = {}
                        metric = col.rsplit('_', 1)[0]
                        metrics.add(metric)
                        if item['Company Name'] not in years_data[year]:
                            years_data[year][item['Company Name']] = {}
                        years_data[year][item['Company Name']][metric] = value
        
        # Second pass: create year sheets
        for year in sorted(years_data.keys(), reverse=True):
            sheet_name = f"{sheet_type}_{year}"
            year_data = []
            
            # Add all companies
            for company_name, company_info in companies.items():
                row = {
                    'Company Name': company_name,
                    'BSE Tag': company_info['BSE Tag'],
                    'NSE Tag': company_info['NSE Tag']
                }
                
                # Add metrics for this year
                company_year_data = years_data[year].get(company_name, {})
                for metric in sorted(metrics):
                    row[metric] = company_year_data.get(metric, '')
                
                year_data.append(row)
            
            final_data[sheet_name] = year_data
    
    return final_data

def write_excel(data):
    """Write organized data to Excel"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(PATHS['output_dir'], 
                                  f'company_data_{timestamp}.xlsx')
        
        final_data = organize_sheets_by_year(data)
        
        if not final_data:
            print("No data to write")
            return
        
        # Sort sheets
        static_sheets = ['Company_Info', 'Main_Metrics']
        year_sheets = sorted(
            [sheet for sheet in final_data.keys() if sheet not in static_sheets],
            key=lambda x: (x.split('_')[0], x.split('_')[1]),
            reverse=True
        )
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Write static sheets
            for sheet in static_sheets:
                if sheet in final_data and final_data[sheet]:
                    df = pd.DataFrame(final_data[sheet])
                    df.to_excel(
                        excel_writer=writer,
                        sheet_name=sheet,
                        index=False
                    )
            
            # Write year sheets
            for sheet in year_sheets:
                if final_data[sheet]:
                    df = pd.DataFrame(final_data[sheet])
                    df.to_excel(
                        excel_writer=writer,
                        sheet_name=sheet,
                        index=False
                    )
        
        print(f"Data written to {output_file}")
    
    except Exception as e:
        print(f"Excel write failed: {str(e)}")
        try:
            backup = output_file.replace('.xlsx', '_backup.xlsx')
            with pd.ExcelWriter(backup, engine='openpyxl') as writer:
                df = pd.DataFrame({'Error': ['Data processing failed']})
                df.to_excel(
                    excel_writer=writer,
                    sheet_name='Error_Log',
                    index=False
                )
            print(f"Error log written to {backup}")
        except Exception as backup_error:
            print(f"Failed to write backup: {str(backup_error)}")
    finally:
        print("Processing completed")

def process_files():
    """Process all HTML files and return data dictionary"""
    sheets_data = {sheet: [] for sheet in SHEET_CONFIG.keys()}
    
    files = get_all_files()
    total_files = len(files)
    
    print(f"\nProcessing {total_files} files...")
    
    for index, file in enumerate(files, 1):
        print(f"\rProcessing file {index}/{total_files}: {file}", end='')
        
        try:
            with open(os.path.join(PATHS['html_dir'], file), 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                
                company_info = extract_company_info(soup)
                if not company_info:
                    continue
                
                sheets_data['Company_Info'].append(company_info)
                
                main_data = extract_main_tables(soup)
                sheets_data['Main_Metrics'].append({**company_info, **main_data})
                
                for sheet in SHEET_CONFIG.keys():
                    if sheet not in ['Company_Info', 'Main_Metrics']:
                        data = extract_table_data(soup, sheet)
                        if data:
                            sheets_data[sheet].append({**company_info, **data})
        except Exception as e:
            print(f"\nError processing {file}: {str(e)}")
            continue
    
    print("\nProcessing completed!")
    return sheets_data

def main():
    """Main execution function"""
    sheets_data = process_files()
    write_excel(sheets_data)

if __name__ == "__main__":
    main()
