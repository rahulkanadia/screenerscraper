
import pandas as pd
import numpy as np
import os
import xlsxwriter

# --- 1. FILE PATHS ---
DS1_PATH = "F:\projects\screenerscraper\dataset1.csv"              # Market & Shareholding
DS2_PATH = "F:\projects\screenerscraper\dataset2.csv"              # Technicals
SCREENER_PATH = "F:\projects\screenerscraper\screenerscraped-2026-03-17_15-49.csv"  # The pipeline output
OUTPUT_PATH = "master_valuation_matrix.xlsx" # NOW XLSX
ORPHAN_PATH = "orphaned_data.csv"

# --- 2. HELPER: EXCEL COLUMN LETTERS ---
def col_letter(idx):
    """Converts column index (0, 1) to Excel letters (A, B)"""
    result = ""
    while idx >= 0:
        result = chr(idx % 26 + 65) + result
        idx = idx // 26 - 1
    return result

# --- 3. SECTOR RELEVANCE TAGGING ---
def get_relevance(sector):
    sector = str(sector).upper()
    if any(bank in sector for bank in ["BANK", "FINANCE", "NBFC"]):
        return "LOW", "HIGH", "LOW" # PE, PB, EV
    elif any(heavy in sector for heavy in ["TELECOM", "INFRASTRUCTURE", "POWER", "OIL", "MINING", "STEEL"]):
        return "MED", "LOW", "HIGH" # PE, PB, EV
    else:
        return "HIGH", "LOW", "LOW" # PE, PB, EV (Default)

def main():
    print("Loading datasets...")
    try:
        df1 = pd.read_csv(DS1_PATH, dtype=str)
        df2 = pd.read_csv(DS2_PATH, dtype=str)
        df_screen = pd.read_csv(SCREENER_PATH, dtype=str)
    except Exception as e:
        print(f"Error loading files: {e}")
        return

    # --- 4. MERGE DATASET 1 & 2 ---
    df_manual = pd.merge(df1, df2, on=["NSE Symbol", "BSE Code"], how="outer")

    # --- 5. PIVOT SCREENER DATA ---
    print("Pivoting Screener data...")
    static_cols = ['NSE Symbol', 'BSE Code', 'Company Name', 'Sector', 'Industry']
    df_base = df_screen[static_cols].drop_duplicates()

    wide_data = {}
    for _, row in df_screen.iterrows():
        key = row['NSE Symbol'] if pd.notna(row['NSE Symbol']) and row['NSE Symbol'] != "N/A" else row['BSE Code']
        if key not in wide_data:
            wide_data[key] = {}
            
        metric = row['Metric']
        for col in df_screen.columns:
            if col not in static_cols + ['Section', 'Metric'] and pd.notna(row[col]) and row[col].strip() != "":
                col_name = f"{metric}_{col}".replace(" ", "_").replace("-", "_")
                wide_data[key][col_name] = row[col]

    df_wide_screen = pd.DataFrame.from_dict(wide_data, orient='index').reset_index()
    df_wide_screen.rename(columns={'index': 'Merge_Key'}, inplace=True)

    df_base['Merge_Key'] = np.where((df_base['NSE Symbol'].notna()) & (df_base['NSE Symbol'] != "N/A"), df_base['NSE Symbol'], df_base['BSE Code'])
    df_manual['Merge_Key'] = np.where((df_manual['NSE Symbol'].notna()) & (df_manual['NSE Symbol'] != "N/A"), df_manual['NSE Symbol'], df_manual['BSE Code'])

    df_screen_final = pd.merge(df_base, df_wide_screen, on="Merge_Key", how="left")

    # --- 6. MASTER MERGE & ORPHANING ---
    print("Executing Master Merge...")
    master_df = pd.merge(df_screen_final, df_manual, on="Merge_Key", how="outer", indicator=True)
    
    orphans = master_df[master_df['_merge'] != 'both'].copy()
    orphans.to_csv(ORPHAN_PATH, index=False)
    print(f"Isolated {len(orphans)} orphaned records to {ORPHAN_PATH}.")

    master = master_df[master_df['_merge'] == 'both'].copy()
    
    master[['Relevance_PE', 'Relevance_PB', 'Relevance_EV']] = master.apply(
        lambda row: pd.Series(get_relevance(row['Sector'])), axis=1
    )

    # --- 7. EXACT COLUMN LAYOUT ---
    columns = [
        "NSE_Symbol", "BSE_Code", "Company_Name", "Sector", "Industry",
        "Current_Price", "Market_Cap", "52W_High", "52W_Low", "%_Away_52W_High",
        "Promoter_%", "FII_%", "DII_%", "Public_%",
        "2024_High", "2024_Low", "2024_Close", "2025_Exit_Price",
        "2025_Yearly_Pivot", "2025_R1", "2025_S1", "Distance_to_Pivot_%",
        "TTM_Sales", "TTM_Expenses", "TTM_Operating_Profit", "TTM_Net_Profit", "TTM_EPS",
        "Total_Debt", "Cash_Equivalents", "Book_Value", "Shares_Outstanding",
        "ROE_Last_Year", "ROE_3Yr", "ROCE_Last_Year", "OPM_%",
        "1Yr_Sales_Growth", "3Yr_Sales_Growth", "1Yr_Profit_Growth", "3Yr_Profit_Growth",
        "5Yr_Median_PE", "5Yr_Median_PB", "5Yr_Median_EV",
        "Sector_Median_PE", "Active_PE_Anchor", "Active_PB_Anchor", "Active_EV_Anchor",
        "Q3_FY25_EPS", "Q4_FY25_EPS", "Q3_FY26_EPS",
        "Est_Q4_FY26_EPS", "FY26E_EPS", "FY26E_EBITDA",
        "FV_1_PE", "FV_2_EVEBITDA", "FV_3_PB", "FV_4_Graham",
        "Relevance_PE", "Relevance_PB", "Relevance_EV",
        "Sector_Weighted_FV", "Sector_Agnostic_FV", "Market_Weighted_FV"
    ]

    col_map = {col: col_letter(idx) for idx, col in enumerate(columns)}
    def R(col_name): return f"{col_map[col_name]}4"

    # --- 8. BUILD ROW 2: NATIVE EXCEL FORMULAS ---
    formulas = {c: "" for c in columns} 
    
    formulas["%_Away_52W_High"] = f"=IFERROR(({R('Current_Price')}-{R('52W_High')})/{R('52W_High')}, \"\")"
    formulas["2025_Yearly_Pivot"] = f"=IFERROR(({R('2024_High')}+{R('2024_Low')}+{R('2024_Close')})/3, \"\")"
    formulas["2025_R1"] = f"=IFERROR((2*{R('2025_Yearly_Pivot')})-{R('2024_Low')}, \"\")"
    formulas["2025_S1"] = f"=IFERROR((2*{R('2025_Yearly_Pivot')})-{R('2024_High')}, \"\")"
    formulas["Distance_to_Pivot_%"] = f"=IFERROR(({R('Current_Price')}-{R('2025_Yearly_Pivot')})/{R('2025_Yearly_Pivot')}, \"\")"
    
    formulas["Shares_Outstanding"] = f"=IFERROR({R('Market_Cap')}/{R('Current_Price')}, \"\")"
    
    formulas["Sector_Median_PE"] = f"=IFERROR(MEDIAN(IF(${col_map['Sector']}$4:${col_map['Sector']}$5000={R('Sector')}, ${col_map['5Yr_Median_PE']}$4:${col_map['5Yr_Median_PE']}$5000)), \"\")"
    formulas["Active_PE_Anchor"] = f"=IFERROR(IF(ISBLANK({R('5Yr_Median_PE')}), {R('Sector_Median_PE')}, {R('5Yr_Median_PE')}), {R('Sector_Median_PE')})"
    formulas["Active_PB_Anchor"] = f"=IFERROR(IF(ISBLANK({R('5Yr_Median_PB')}), 1.5, {R('5Yr_Median_PB')}), 1.5)" 
    formulas["Active_EV_Anchor"] = f"=IFERROR(IF(ISBLANK({R('5Yr_Median_EV')}), 10, {R('5Yr_Median_EV')}), 10)"  
    
    formulas["Est_Q4_FY26_EPS"] = f"=IFERROR(({R('Q4_FY25_EPS')}/{R('Q3_FY25_EPS')})*{R('Q3_FY26_EPS')}, {R('Q3_FY26_EPS')}*(1+IFERROR({R('3Yr_Profit_Growth')}, 0.1)))"
    formulas["FY26E_EPS"] = f"=IFERROR({R('TTM_EPS')}-{R('Q4_FY25_EPS')}+{R('Est_Q4_FY26_EPS')}, {R('TTM_EPS')})"
    formulas["FY26E_EBITDA"] = f"=IFERROR({R('TTM_Operating_Profit')}*(1+IFERROR({R('3Yr_Profit_Growth')}, 0.1)), {R('TTM_Operating_Profit')})"
    
    formulas["FV_1_PE"] = f"=IFERROR({R('FY26E_EPS')}*{R('Active_PE_Anchor')}, \"\")"
    formulas["FV_2_EVEBITDA"] = f"=IFERROR((({R('FY26E_EBITDA')}*{R('Active_EV_Anchor')})-{R('Total_Debt')}+{R('Cash_Equivalents')})/{R('Shares_Outstanding')}, \"\")"
    formulas["FV_3_PB"] = f"=IFERROR({R('Book_Value')}*{R('Active_PB_Anchor')}, \"\")"
    formulas["FV_4_Graham"] = f"=IFERROR(SQRT(22.5*{R('TTM_EPS')}*{R('Book_Value')}), \"Negative Core\")"

    formulas["Sector_Weighted_FV"] = f"=IF({R('Relevance_PB')}=\"HIGH\", ({R('FV_3_PB')}*0.7)+({R('FV_1_PE')}*0.3), IF({R('Relevance_EV')}=\"HIGH\", ({R('FV_2_EVEBITDA')}*0.7)+({R('FV_1_PE')}*0.3), {R('FV_1_PE')}))"
    formulas["Sector_Agnostic_FV"] = f"=IFERROR(AVERAGE({R('FV_1_PE')}, {R('FV_2_EVEBITDA')}, {R('FV_3_PB')}, {R('FV_4_Graham')}), \"\")"
    formulas["Market_Weighted_FV"] = f"=IFERROR({R('Sector_Weighted_FV')} * IF({R('Market_Cap')}>50000, 1.0, IF({R('Market_Cap')}>5000, 0.9, 0.75)), \"\")"

    # --- 9. EXPORT TO XLSX ---
    print(f"Writing Master Matrix to {OUTPUT_PATH}...")
    
    workbook = xlsxwriter.Workbook(OUTPUT_PATH)
    worksheet = workbook.add_worksheet("Valuation Matrix")
    
    # Formats
    header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
    formula_format = workbook.add_format({'bg_color': '#E8F8F5', 'font_color': '#0E6251'}) # Light green to denote formula row
    
    # Write Headers (Row 1 / Index 0)
    for col_num, col_name in enumerate(columns):
        worksheet.write(0, col_num, col_name, header_format)
        
    # Write Formulas (Row 2 / Index 1) - xlsxwriter natively handles '=' strings as formulas
    for col_num, col_name in enumerate(columns):
        if formulas[col_name]:
            worksheet.write_formula(1, col_num, formulas[col_name], formula_format)
        else:
            worksheet.write(1, col_num, "", formula_format)
            
    # Row 3 / Index 2 is implicitly left blank by jumping to row 3 for data
    
    # Write Data (Row 4+ / Index 3+)
    row_idx = 3
    for _, row in master.iterrows():
        for col_num, col_name in enumerate(columns):
            alt_name_1 = col_name.replace("TTM_", "") + "_TTM"
            alt_name_2 = col_name.replace("_", " ")
            
            if col_name in master.columns:
                val = row[col_name]
            elif alt_name_1 in master.columns:
                val = row[alt_name_1]
            elif alt_name_2 in master.columns:
                val = row[alt_name_2]
            else:
                val = "" 
                
            # Clean up floats vs strings for Excel
            if pd.notna(val) and val != "":
                try:
                    worksheet.write_number(row_idx, col_num, float(val))
                except ValueError:
                    worksheet.write_string(row_idx, col_num, str(val))
            else:
                worksheet.write_blank(row_idx, col_num, "")
                
        row_idx += 1

    workbook.close()
    print(f":white_check_mark: Success! Master Matrix saved to {OUTPUT_PATH}. Ready for manual drag-down.")

if __name__ == "__main__":
    main()

