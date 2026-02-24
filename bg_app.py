import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. SETUP LOCAL STORAGE ---
LOGS_FILE = "production_logs.csv"
WORKERS_FILE = "workers.txt"
JOBS_FILE = "jobs.txt"

def load_list(file_path, defaults):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return defaults

def save_list(file_path, data_list):
    with open(file_path, "w") as f:
        for item in data_list:
            f.write(f"{item}\n")

# Load existing data
workers = load_list(WORKERS_FILE, ["Prasanth", "RamaSai", "Subodth"])
job_list = load_list(JOBS_FILE, ["SSR501", "SSR502"])

st.title("🏗️ B&G Shopfloor Monitor")

# --- 2. ADMIN PANEL (The "New" Features) ---
with st.expander("⚙️ ADMIN: Manage Staff & Job Codes"):
    st.subheader("Manage Workers")
    new_worker = st.text_input("Add New Worker Name")
    if st.button("➕ Add Worker"):
        if new_worker and new_worker not in workers:
            workers.append(new_worker)
            save_list(WORKERS_FILE, workers)
            st.rerun()

    worker_to_remove = st.selectbox("Remove Worker", ["-- Select --"] + workers)
    if st.button("🗑️ Delete Worker"):
        if worker_to_remove != "-- Select --":
            workers.remove(worker_to_remove)
            save_list(WORKERS_FILE, workers)
            st.rerun()

    st.divider()
    st.subheader("Manage Job Codes")
    new_job = st.text_input("Add New Job Code (e.g. VESSEL-202)")
    if st.button("➕ Add Job"):
        if new_job and new_job not in job_list:
            job_list.append(new_job)
            save_list(JOBS_FILE, job_list)
            st.rerun()

# --- 3. DAILY PRODUCTION ENTRY ---
st.divider()
with st.form("prod_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        supervisor = st.selectbox("Supervisor", ["Prasanth", "RamaSai", "Subodth"])
        selected_worker = st.selectbox("Worker", workers)
        selected_job = st.selectbox("Job Code", job_list)
    with col2:
        hours = st.number_input("Man-Hours Worked", min_value=0.0, step=0.5)
        activity = st.selectbox("Activity", ["Welding", "Fitup", "Grinding", "Marking"])
    
    if st.form_submit_button("Submit Production Log"):
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "Supervisor": supervisor,
            "Worker": selected_worker,
            "Job_Code": selected_job,
            "Hours": hours,
            "Activity": activity
        }])
        
        # Save logs to file
        if os.path.exists(LOGS_FILE):
            df = pd.read_csv(LOGS_FILE)
            df = pd.concat([df, new_row], ignore_index=True)
        else:
            df = new_row
        df.to_csv(LOGS_FILE, index=False)
        st.success(f"Log saved for {selected_worker}")

# --- 4. DATA EXPORT ---
st.divider()
if os.path.exists(LOGS_FILE):
    df_view = pd.read_csv(LOGS_FILE)
    st.download_button("📥 DOWNLOAD DATA TO EXCEL", df_view.to_csv(index=False), "bg_prod_data.csv")
    st.dataframe(df_view.sort_values(by="Timestamp", ascending=False))
