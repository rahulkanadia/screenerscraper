import json
import os

def convert_metrics_txt(txt_path, json_path):
    if not os.path.exists(txt_path): return
    with open(txt_path, 'r', encoding='utf-8') as f: lines = f.readlines()
    
    metrics_list = []
    current_section = "Uncategorized"
    
    for line in lines:
        if not line.strip(): continue
        indent = len(line) - len(line.lstrip())
        text = line.strip()
        
        if indent == 0:
            current_section = text
        else:
            metrics_list.append({
                "Section": current_section,
                "Metric": text,
                "Source": "HTML", 
                "Active": True
            })
            
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metrics_list, f, indent=4)
    print(f":white_check_mark: Converted Metrics to {json_path}")

def convert_sectors_txt(txt_path, json_path):
    if not os.path.exists(txt_path): return
    with open(txt_path, 'r', encoding='utf-8') as f: lines = f.readlines()
    
    sectors_list = []
    levels = {0: "", 1: "", 2: "", 3: ""}
    
    for line in lines:
        if not line.strip(): continue
        indent = (len(line) - len(line.lstrip())) // 2
        text = line.strip()
        levels[indent] = text
        
        # Only save the leaf nodes (Industries) with their full hierarchy
        if indent == 3:
            sectors_list.append({
                "Broad Sector": levels[0],
                "Sector": levels[1],
                "Broad Industry": levels[2],
                "Industry": levels[3],
                "Active": True
            })
            
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(sectors_list, f, indent=4)
    print(f":white_check_mark: Converted Sectors to {json_path}")

# Execute
convert_metrics_txt("metrics.txt", "metrics.json")
convert_sectors_txt("sectors.txt", "sectors.json")
