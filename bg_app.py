import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os

# --- 1. SETUP & TIMEZONE ---
IST = pytz.timezone('Asia/Kolkata')
LOGS_FILE = "production_logs.csv"
WORKERS_FILE = "workers.txt"
JOBS_FILE = "jobs.txt"

# Units Mapping
UNITS = {
    "Welding": "Meters (Mts)", "Grinding": "Amount/Length (Mts)", 
    "Drilling": "Quantity (Nos)", "Cutting (Plasma/Gas)": "Meters (Mts)",
    "Fitting/Assembly": "Joints/Points (Nos)", "Marking": "Layouts (Nos)",
    "Buffing/Polishing": "Square Feet (Sq Ft)", "Bending/Rolling": "Components (Nos)",
    "Hydro-Testing": "Equipment (Nos)", "Painting/Coating": "Square Meters (Sq M)",
    "Dispatch/Loading": "Weight (Tons/Kgs)"
}

# FIXED HEADERS FOR BOTH TABLES
HEADERS = ["Timestamp", "Supervisor", "Worker", "Job_Code", "Activity", "Output", "Unit", "Hours", "Category", "Notes"]

def load_list(file_path, defaults):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return defaults

st.set_page_config(page_title="B&G Production", layout="wide")
st.title("🏗️ B&G Production & Progress Tracker")

workers = load_list(WORKERS_FILE, ["Prasanth", "RamaSai", "Subodth", "Naresh", "Ravindra"])
job_list = load_list(JOBS_FILE, ["SSR501", "SSR502", "VESSEL-101"])

# --- 2. ENTRY FORM ---
with st.form("prod_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        supervisor = st.selectbox("Supervisor", ["Prasanth", "RamaSai", "Subodth"])
        worker = st.selectbox("Worker Name", workers)
        category = st.selectbox("Worker Category", ["Welder (Grade A/IBR)", "Welder (Grade B)", "Fitter", "Grinder", "Helper"])
        job_code = st.selectbox("Job Code", job_list)
    with col2:
        activity = st.selectbox("Activity", list(UNITS.keys()))
        unit = UNITS[activity]
        output = st.number_input(f"Output ({unit})", min_value=0.0)
        hours = st.number_input("Man-Hours", min_value=0.0, step=0.5)
        notes = st.text_area("Remarks")

    if st.form_submit_button("Submit Production Log"):
        ts = datetime.now(IST).strftime('%Y-%m-%d %H:%M')
        new_data = pd.DataFrame([[ts, supervisor, worker, job_code, activity, output, unit, hours, category, notes]], columns=HEADERS)
        
        if os.path.exists(LOGS_FILE):
            df = pd.read_csv(LOGS_FILE)
            # FORCE REPAIR: Rename any old columns to match HEADERS
            df = df.rename(columns={"Job": "Job_Code", "Remarks": "Notes", "Job_code": "Job_Code"})
            df = pd.concat([df, new_data], ignore_index=True)
        else:
            df = new_data
        
        df.to_csv(LOGS_FILE, index=False)
        st.success("✅ Logged Successfully!")
        st.rerun()

# --- 3. DATA TABLES ---
st.divider()
if os.path.exists(LOGS_FILE):
    df = pd.read_csv(LOGS_FILE)
    # Ensure all required columns exist in the display
    df = df.reindex(columns=HEADERS)
    
    # TABLE 1: JOB PROGRESS SUMMARY
    st.subheader("📊 Job Progress Summary")
    summary = df.groupby(['Job_Code', 'Activity', 'Unit']).agg({'Output': 'sum', 'Hours': 'sum'}).reset_index()
    st.table(summary)

    # TABLE 2: VIEW ALL DETAILED LOGS
    with st.expander("🔍 View All Detailed Logs", expanded=True):
        st.dataframe(df.sort_values(by="Timestamp", ascending=False), use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel Report", csv, "BG_Production_Report.csv")
else:
    st.info("No records found.")
