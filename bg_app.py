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

ACTIVITY_UNITS = {
    "Welding": "Meters (Mts)", "Grinding": "Amount/Length (Mts)", 
    "Drilling": "Quantity (Nos)", "Cutting (Plasma/Gas)": "Meters (Mts)",
    "Fitting/Assembly": "Joints/Points (Nos)", "Marking": "Layouts (Nos)",
    "Buffing/Polishing": "Square Feet (Sq Ft)", "Bending/Rolling": "Components (Nos)",
    "Hydro-Testing": "Equipment (Nos)", "Painting/Coating": "Square Meters (Sq M)",
    "Dispatch/Loading": "Weight (Tons/Kgs)"
}

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
        # CAPTURING IST TIME
        timestamp = datetime.now(IST).strftime('%Y-%m-%d %H:%M')
        
        # ALIGNING ALL COLUMN NAMES
        new_row = pd.DataFrame([{
            "Timestamp": timestamp,
            "Supervisor": supervisor,
            "Worker": selected_worker,
            "Category": category,
            "Job_Code": selected_job, # Using 'Job_Code' consistently
            "Activity": activity,
            "Output": output_val,
            "Unit": unit_label,
            "Hours": hours,
            "Notes": notes
        }])
        
        if os.path.exists(LOGS_FILE):
            df = pd.read_csv(LOGS_FILE)
            df = pd.concat([df, new_row], ignore_index=True)
        else:
            df = new_row
        df.to_csv(LOGS_FILE, index=False)
        st.success(f"✅ Logged successfully at {timestamp}!")
        st.rerun()

# --- 3. PROGRESS SUMMARY & DATA VIEW ---
st.divider()
if os.path.exists(LOGS_FILE):
    df_view = pd.read_csv(LOGS_FILE)
    
    # Progress Summary using 'Job_Code'
    st.subheader("📊 Job Progress Summary")
    if 'Job_Code' in df_view.columns:
        summary = df_view.groupby(['Job_Code', 'Activity', 'Unit']).agg({
            'Output': 'sum',
            'Hours': 'sum'
        })
        st.table(summary)

    with st.expander("🔍 View All Detailed Logs"):
        # Sort by Timestamp so latest is on top
        st.dataframe(df_view.sort_values(by="Timestamp", ascending=False), use_container_width=True)
        csv = df_view.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel Report", csv, f"BG_Prod_{datetime.now(IST).strftime('%d%m%Y')}.csv")
else:
    st.info("No records found. Submit your first production log above.")
