
# --- app.py ---

import streamlit as st
import pandas as pd
import json
import os
import sys

# --- Page Configuration ---
st.set_page_config(page_title="Screener.in Data Pipeline", layout="wide", page_icon=":chart_with_upwards_trend:")

CONFIG_FILE = "path_config.json"

# --- Dynamic Path Management ---
def load_path_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    # Default fallback guesses
    return {
        "html_dir": r"F:\projects\screenerscraper\screenerscraper\screenerhtml",
        "metrics_json": r"F:\projects\screenerscraper\screenerscraper\metrics.json",
        "sectors_json": r"F:\projects\screenerscraper\screenerscraper\sectors.json",
        "backend_dir": r"F:\projects\screenerscraper\screenerscraper"
    }

paths = load_path_config()

# --- SIDEBAR: EXPLICIT PATH CONFIGURATION ---
with st.sidebar:
    st.header(":file_folder: Explicit Paths")
    st.caption("Point these to the exact locations on your drive.")
    
    backend_dir = st.text_input("Backend Scripts Folder", paths.get("backend_dir", ""))
    html_dir = st.text_input("HTML Pages Folder", paths.get("html_dir", ""))
    metrics_json_path = st.text_input("Metrics JSON File", paths.get("metrics_json", ""))
    sectors_json_path = st.text_input("Sectors JSON File", paths.get("sectors_json", ""))
    
    if st.button(":floppy_disk: Save & Reload Paths", type="primary", use_container_width=True):
        new_paths = {
            "html_dir": html_dir.strip('\"\''),
            "metrics_json": metrics_json_path.strip('\"\''),
            "sectors_json": sectors_json_path.strip('\"\''),
            "backend_dir": backend_dir.strip('\"\'')
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_paths, f, indent=4)
        st.success("Paths locked in!")
        st.rerun()

# --- DYNAMIC BACKEND IMPORT ---
# We inject the explicitly provided backend directory directly into Python's system path
backend_loaded = False
if os.path.exists(backend_dir):
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    try:
        # Now it imports directly from the folder you specified, no guessing.
        from screenerscraper_getmetrics import generate_metrics_json
        from screenerscraper_getsectors import generate_sectors_json
        from screenerscraper import run_parser, run_shareholding_parser
        backend_loaded = True
    except ImportError as e:
        st.sidebar.error(f"Import Error: {e}. Check the Backend Scripts Folder path.")
else:
    st.sidebar.warning(":warning: Backend directory not found. Please set it above.")

# --- Helper Functions ---
def load_json_df(filepath, default_cols):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data: return pd.DataFrame(data)
        except Exception as e:
            st.error(f"Failed to load {filepath}: {e}")
    return pd.DataFrame(columns=default_cols)

def save_json_df(df, filepath):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(df.to_dict(orient='records'), f, indent=4)
        return True
    except Exception as e:
        st.error(f"Failed to save {filepath}: {e}")
        return False

# --- Main Application UI ---
st.title("Screener.in Data Pipeline")
if not backend_loaded:
    st.error(":rotating_light: Backend scripts disconnected. Please set the correct 'Backend Scripts Folder' path in the sidebar.")
    st.stop()

tab1, tab2, tab3 = st.tabs([":rocket: Scrape Control", ":microscope: Data Playground", ":gear: JSON Configuration"])

# ==========================================
# TAB 1: SCRAPE CONTROL
# ==========================================
with tab1:
    col1, col2, col3, col4 = st.columns([1.2, 1.5, 1, 1])

    with col1:
        st.subheader("1. Setup & Execute")
        
        st.markdown("**Phase 1: Meta Configuration**")
        if st.button("Generate Meta JSONs", use_container_width=True):
            with st.spinner(f"Scanning HTML files in {html_dir}..."):
                res1, msg1 = generate_metrics_json(html_dir, metrics_json_path)
                res2, msg2 = generate_sectors_json(html_dir, sectors_json_path)
                if res1 and res2:
                    st.success("JSONs successfully built! Check the config tab.")
                else:
                    st.error(f"{msg1} | {msg2}")

        st.divider()

        st.markdown("**Phase 2: Database Export**")
        if st.button("Export Screened Companies to CSV", type="primary", use_container_width=True):
            
            df_sec = load_json_df(sectors_json_path, ["Broad Sector", "Sector", "Broad Industry", "Industry", "Active"])
            df_met = load_json_df(metrics_json_path, ["Section", "Metric", "Source", "Active"])
            
            active_sectors = df_sec[df_sec['Active'] == True]['Industry'].tolist() if not df_sec.empty else []
            active_metrics = df_met[df_met['Active'] == True].to_dict('records') if not df_met.empty else []

            active_years = [y for y in range(2013, 2027) if st.session_state.get(f"yr_{y}", False)]
            active_qtrs = [q for q, key in zip(["Mar", "Jun", "Sep", "Dec"], ["q_mar", "q_jun", "q_sep", "q_dec"]) if st.session_state.get(key, True)]
            inc_ttm = st.session_state.get("inc_ttm", True)

            if not active_metrics:
                st.error("No active metrics found. Please configure JSONs first.")
            else:
                st.info("Pipeline Initialized. Locking UI during extraction...")
                
                st.markdown("##### :gear: Financial Data Extraction")
                fin_status = st.empty()
                fin_progress = st.progress(0)
                
                run_parser(html_dir, active_years, active_qtrs, inc_ttm, active_metrics, active_sectors, fin_progress, fin_status)
                fin_status.success("Financial CSV Built Successfully!")

                st.markdown("##### :busts_in_silhouette: Shareholding Extraction")
                shp_status = st.empty()
                shp_progress = st.progress(0)
                
                run_shareholding_parser(html_dir, active_years, active_qtrs, active_sectors, shp_progress, shp_status)
                shp_status.success("Shareholding CSV Built Successfully!")
                
                st.balloons()

    with col2:
        st.subheader("2. System Console")
        st.info("Execution is strictly synchronous to guarantee 100% data integrity. Paths are mapped explicitly via the sidebar.")

    with col3:
        st.subheader("3. Extract Periods")
        st.checkbox("Include TTM (Trailing 12 Months)", value=True, key="inc_ttm")
        
        y_col1, y_col2 = st.columns(2)
        with y_col1:
            st.markdown("**Recent Years**")
            for y in range(2026, 2020, -1):
                st.checkbox(str(y), value=(y in [2026, 2025]), key=f"yr_{y}")
        with y_col2:
            st.markdown("**Historical**")
            for y in range(2020, 2013, -1):
                st.checkbox(str(y), value=False, key=f"yr_{y}")

        st.markdown("**Quarters**")
        q_col1, q_col2 = st.columns(2)
        with q_col1:
            st.checkbox("Mar (Q4)", value=True, key="q_mar")
            st.checkbox("Jun (Q1)", value=True, key="q_jun")
        with q_col2:
            st.checkbox("Sep (Q2)", value=True, key="q_sep")
            st.checkbox("Dec (Q3)", value=True, key="q_dec")

    with col4:
        st.subheader("4. Target Overview")
        df_sec = load_json_df(sectors_json_path, ["Industry", "Active"])
        active_sec = df_sec[df_sec['Active'] == True].shape[0] if not df_sec.empty else 0

        df_met = load_json_df(metrics_json_path, ["Metric", "Active"])
        active_met = df_met[df_met['Active'] == True].shape[0] if not df_met.empty else 0

        st.metric(label="Active Target Industries", value=active_sec)
        st.metric(label="Active Financial Metrics", value=active_met)

# ==========================================
# TAB 2: DATA PLAYGROUND
# ==========================================
with tab2:
    st.info("Interactive Query Engine will connect here once database ingestion is complete.")

# ==========================================
# TAB 3: JSON CONFIGURATION
# ==========================================
with tab3:
    st.info("Edits made here update the underlying explicitly mapped .json files.")
    j_col1, j_col2 = st.columns(2)

    with j_col1:
        st.subheader("Sector Configuration")
        df_sectors = load_json_df(sectors_json_path, ["Broad Sector", "Sector", "Broad Industry", "Industry", "Active"])
        edited_sectors = st.data_editor(df_sectors, num_rows="dynamic", use_container_width=True, height=550)
        if st.button(":floppy_disk: Save Sectors", type="primary"):
            if save_json_df(edited_sectors, sectors_json_path): st.success("Saved Sectors!")

    with j_col2:
        st.subheader("Metrics Configuration")
        df_metrics = load_json_df(metrics_json_path, ["Section", "Metric", "Source", "Active"])
        edited_metrics = st.data_editor(df_metrics, num_rows="dynamic", use_container_width=True, height=550)
        if st.button(":floppy_disk: Save Metrics", type="primary"):
            if save_json_df(edited_metrics, metrics_json_path): st.success("Saved Metrics!")

