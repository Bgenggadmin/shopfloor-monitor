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

# Industrial Units Mapping
ACTIVITY_UNITS = {
    "Welding": "Meters (Mts)",
    "Grinding": "Amount/Length (Mts)",
    "Drilling": "Quantity (Nos)",
    "Cutting (Plasma/Gas)": "Meters (Mts)",
    "Fitting/Assembly": "Joints/Points (Nos)",
    "Marking": "Layouts (Nos)",
    "Buffing/Polishing": "Square Feet (Sq Ft)",
    "Bending/Rolling": "Components (Nos)",
    "Hydro-Testing": "Equipment (Nos)",
    "Painting/Coating": "Square Meters (Sq M)",
    "Dispatch/Loading": "Weight (Tons/Kgs)"
}

# Helper functions for local lists
def load_list(file_path, defaults):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return defaults

def save_list(file_path, data_list):
    with open(file_path, "w") as f:
        for item in data_list:
            f.write(f"{item}\n")

# Initial Data Load
workers = load_list(WORKERS_FILE, ["Prasanth", "RamaSai", "Subodth", "Naresh", "Ravindra"])
job_list = load_list(JOBS_FILE, ["SSR501", "SSR502", "VESSEL-101"])

st.set_page_config(page_title="B&G Production", layout="wide")
st.title("🏗️ B&G Production & Progress Tracker")

# --- 2. ADMIN PANEL ---
with st.expander("⚙️ ADMIN: Manage Staff & Job Codes"):
    tab1, tab2 = st.tabs(["Workers", "Job Codes"])
    with tab1:
        new_w = st.text_input("New Worker Name")
        if st.button("➕ Add Worker"):
            if new_w and new_w not in workers:
                workers.append(new_w)
                save_list(WORKERS_FILE, workers)
                st.rerun()
        rem_w = st.selectbox("Remove Worker", ["-- Select --"] + workers)
        if st.button("🗑️ Delete Worker") and rem_w != "-- Select --":
            workers.remove(rem_w)
            save_list(WORKERS_FILE, workers)
            st.rerun()
    with tab2:
        new_j = st.text_input("New Job Code")
        if st.button("➕ Add Job"):
            if new_j and new_j not in job_list:
                job_list.append(new_j)
                save_list(JOBS_FILE, job_list)
                st.rerun()

# --- 3. PRODUCTION ENTRY FORM ---
st.divider()
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
        new_row = pd.DataFrame([{
            "Timestamp": timestamp, "Supervisor": supervisor, "Worker": selected_worker,
            "Category": category, "Job": selected_job, "Activity": activity,
            "Output": output_val, "Unit": unit_label, "Hours": hours, "Remarks": notes
        }])
        
        if os.path.exists(LOGS_FILE):
            df = pd.read_csv(LOGS_FILE)
            df = pd.concat([df, new_row], ignore_index=True)
        else:
            df = new_row
        df.to_csv(LOGS_FILE, index=False)
        st.success(f"✅ Logged successfully!")
        st.rerun()

# --- 4. PROGRESS SUMMARY & DATA VIEW ---
st.divider()
if os.path.exists(LOGS_FILE):
    df_view = pd.read_csv(LOGS_FILE)
    
    # Check for the correct columns (Self-Healing)
    required_cols = ['Job', 'Activity', 'Unit', 'Output', 'Hours']
    if all(col in df_view.columns for col in required_cols):
        st.subheader("📊 Job Progress Summary")
        summary = df_view.groupby(['Job', 'Activity', 'Unit']).agg({
            'Output': 'sum',
            'Hours': 'sum'
        })
        st.table(summary)
    else:
        st.error("⚠️ Old data format detected. Please delete 'production_logs.csv' from GitHub or submit a new entry.")

    with st.expander("🔍 View All Detailed Logs"):
        st.dataframe(df_view.sort_values(by="Timestamp", ascending=False), use_container_width=True)
        csv = df_view.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel Report", csv, f"BG_Prod_{datetime.now(IST).strftime('%d%m%Y')}.csv")
else:
    st.info("No records found. Submit your first production log above.")
