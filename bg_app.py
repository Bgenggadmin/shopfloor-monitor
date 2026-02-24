import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os

# --- 1. SETUP & TIMEZONE (IST) ---
IST = pytz.timezone('Asia/Kolkata')
LOGS_FILE = "production_logs.csv"
WORKERS_FILE = "workers.txt"
JOBS_FILE = "jobs.txt"

# Exact Units for B&G shopfloor
ACTIVITY_UNITS = {
    "Welding": "Meters (Mts)", "Grinding": "Amount/Length (Mts)", 
    "Drilling": "Quantity (Nos)", "Cutting (Plasma/Gas)": "Meters (Mts)",
    "Fitting/Assembly": "Joints/Points (Nos)", "Marking": "Layouts (Nos)",
    "Buffing/Polishing": "Square Feet (Sq Ft)", "Bending/Rolling": "Components (Nos)",
    "Hydro-Testing": "Equipment (Nos)", "Painting/Coating": "Square Meters (Sq M)",
    "Dispatch/Loading": "Weight (Tons/Kgs)"
}

# THE MASTER COLUMN HEADERS (Exactly as you want them displayed)
COL_HEADERS = [
    "Timestamp", "Supervisor", "Worker", "Job_Code", 
    "Hours", "Activity", "Notes", "Category", "Output", "Unit"
]

def load_list(file_path, defaults):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return defaults

def save_list(file_path, data_list):
    with open(file_path, "w") as f:
        for item in data_list:
            f.write(f"{item}\n")

workers = load_list(WORKERS_FILE, ["Prasanth", "RamaSai", "Subodth", "Naresh", "Ravindra"])
job_list = load_list(JOBS_FILE, ["SSR501", "SSR502", "VESSEL-101"])

st.set_page_config(page_title="B&G Production", layout="wide")
st.title("🏗️ B&G Production & Progress Tracker")

# --- 2. PRODUCTION ENTRY FORM ---
with st.form("prod_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        supervisor = st.selectbox("Supervisor", ["Prasanth", "RamaSai", "Subodth"])
        selected_worker = st.selectbox("Worker Name", workers)
        category = st.selectbox("Worker Category", ["Welder (Grade A/IBR)", "Welder (Grade B)", "Fitter", "Grinder", "Helper"])
        selected_job = st.selectbox("Job Code", job_list)
    with col2:
        activity = st.selectbox("Activity", list(ACTIVITY_UNITS.keys()))
        unit_label = ACTIVITY_UNITS[activity]
        output_val = st.number_input(f"Output ({unit_label})", min_value=0.0, step=0.1)
        hours = st.number_input("Man-Hours Spent", min_value=0.0, step=0.5)
        notes = st.text_area("📋 Technical Remarks")

    if st.form_submit_button("Submit Production Log"):
        timestamp = datetime.now(IST).strftime('%Y-%m-%d %H:%M')
        
        # New entry mapping to the Master Headers
        new_entry = {
            "Timestamp": timestamp, "Supervisor": supervisor, "Worker": selected_worker,
            "Job_Code": selected_job, "Hours": hours, "Activity": activity,
            "Notes": notes, "Category": category, "Output": output_val, "Unit": unit_label
        }
        
        if os.path.exists(LOGS_FILE):
            df = pd.read_csv(LOGS_FILE)
            # FIX: If old data used 'Job', move it to 'Job_Code'
            if 'Job' in df.columns:
                df['Job_Code'] = df['Job_Code'].fillna(df['Job'])
            # FIX: If old data used 'Remarks', move it to 'Notes'
            if 'Remarks' in df.columns:
                df['Notes'] = df['Notes'].fillna(df['Remarks'])
                
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        else:
            df = pd.DataFrame([new_entry])
            
        df.to_csv(LOGS_FILE, index=False)
        st.success(f"✅ Logged successfully at {timestamp}!")
        st.rerun()

# --- 3. PROGRESS SUMMARY & DATA VIEW ---
st.divider()
if os.path.exists(LOGS_FILE):
    df_view = pd.read_csv(LOGS_FILE)
    
    # FORCED CLEANUP: Ensure only our Master Headers are shown in the exact order
    df_clean = df_view.reindex(columns=COL_HEADERS)

    st.subheader("📊 Job Progress Summary")
    # Group by Job_Code for the summary table
    summary = df_clean.groupby(['Job_Code', 'Activity', 'Unit']).agg({
        'Output': 'sum', 'Hours': 'sum'
    }).reset_index()
    st.table(summary)

    with st.expander("🔍 View All Detailed Logs", expanded=True):
        # Shows newest entries first with perfectly aligned columns
        st.dataframe(df_clean.sort_values(by="Timestamp", ascending=False), use_container_width=True)
        
        csv = df_clean.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel Report", csv, f"BG_Prod_{datetime.now(IST).strftime('%d%m%Y')}.csv")
else:
    st.info("No records found. Submit your first production log above.")
