import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
from github import Github

# --- 1. SETUP & TIMEZONE (IST) ---
IST = pytz.timezone('Asia/Kolkata')
LOGS_FILE = "production_logs.csv"
WORKERS_FILE = "workers.txt"
JOBS_FILE = "jobs.txt"

UNITS = {
    "Welding": "Meters (Mts)", "Grinding": "Amount/Length (Mts)", 
    "Drilling": "Quantity (Nos)", "Cutting (Plasma/Gas)": "Meters (Mts)",
    "Fitting/Assembly": "Joints/Points (Nos)", "Marking": "Layouts (Nos)",
    "Buffing/Polishing": "Square Feet (Sq Ft)", "Bending/Rolling": "Components (Nos)",
    "Hydro-Testing": "Equipment (Nos)", "Painting/Coating": "Square Meters (Sq M)",
    "Dispatch/Loading": "Weight (Tons/Kgs)"
}

HEADERS = ["Timestamp", "Supervisor", "Worker", "Job_Code", "Activity", "Unit", "Output", "Hours", "Notes"]

# --- 2. GITHUB SYNC ---
def sync_to_github(file_path):
    try:
        if "GITHUB_TOKEN" in st.secrets:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["GITHUB_REPO"])
            with open(file_path, "r") as f:
                content = f.read()
            try:
                contents = repo.get_contents(file_path)
                repo.update_file(contents.path, f"Sync {datetime.now(IST)}", content, contents.sha)
            except:
                repo.create_file(file_path, "Initial Create", content)
    except Exception as e:
        st.error(f"Sync Error: {e}")

def load_list(file_path, defaults):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return defaults

st.set_page_config(page_title="B&G Production", layout="wide")
st.title("🏗️ B&G Production & Progress Tracker")

workers = load_list(WORKERS_FILE, ["Prasanth", "RamaSai", "Subodth", "Sunil", "Naresh", "Ravindra"])
job_list = load_list(JOBS_FILE, ["SSR501", "SSR502", "VESSEL-101"])

# --- 3. ENTRY FORM (FIXED LIVE UNIT UPDATING) ---
# Use columns OUTSIDE the form for the live-updating dropdowns
col1, col2 = st.columns(2)
with col1:
    supervisor = st.selectbox("Supervisor", ["Prasanth", "RamaSai", "Sunil", "Ravindra", "Naresh", "Subodth"])
    worker = st.selectbox("Worker Name", workers)
    job_code = st.selectbox("Job Code", job_list)
with col2:
    # This selection now triggers an immediate change in unit_label
    activity = st.selectbox("Activity", list(UNITS.keys()))
    unit_label = UNITS[activity] # <--- THIS NOW UPDATES INSTANTLY
    output = st.number_input(f"Output ({unit_label})", min_value=0.0)
    hours = st.number_input("Man-Hours Spent", min_value=0.0, step=0.5)
    notes = st.text_area("Remarks/Notes")

if st.button("🚀 Submit Production Log"):
    ts = datetime.now(IST).strftime('%Y-%m-%d %H:%M')
    new_row = [ts, supervisor, worker, job_code, activity, unit_label, output, hours, notes]
    
    if os.path.exists(LOGS_FILE):
        try:
            df = pd.read_csv(LOGS_FILE)
            df = df.loc[:, ~df.columns.duplicated()]
            df = df.rename(columns={'Job': 'Job_Code', 'Remarks': 'Notes'})
            new_df = pd.DataFrame([new_row], columns=HEADERS)
            df = pd.concat([df[HEADERS], new_df], ignore_index=True)
        except:
            df = pd.DataFrame([new_row], columns=HEADERS)
    else:
        df = pd.DataFrame([new_row], columns=HEADERS)
    
    df.to_csv(LOGS_FILE, index=False)
    sync_to_github(LOGS_FILE)
    st.success(f"✅ Logged & Synced at {ts}")
    st.rerun()

# --- 4. DISPLAY ---
st.divider()
if os.path.exists(LOGS_FILE):
    df_view = pd.read_csv(LOGS_FILE).reindex(columns=HEADERS)
    df_display = df_view.sort_values(by="Timestamp", ascending=False)
    st.subheader("📊 Job Progress Summary")
    st.table(df_display.head(10)) 
    with st.expander("🔍 View All Detailed Logs", expanded=True):
        st.dataframe(df_display, use_container_width=True)
        csv = df_view.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel Report", csv, "BG_Production_Report.csv")
        # --- 5. MANAGEMENT & SUMMARY (PHASE 2) ---
st.divider()
st.header("📊 Management & Production Summary")

if os.path.exists(LOGS_FILE):
    # Reload data for fresh view
    df_mngt = pd.read_csv(LOGS_FILE)
    
    # A. SEARCH & FILTER
    st.subheader("🔍 Search Records")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        search_job = st.multiselect("Filter by Job Code", options=df_mngt['Job_Code'].unique())
    with col_s2:
        search_worker = st.multiselect("Filter by Worker", options=df_mngt['Worker'].unique())

    # Apply Filters
    filtered_df = df_mngt.copy()
    if search_job:
        filtered_df = filtered_df[filtered_df['Job_Code'].isin(search_job)]
    if search_worker:
        filtered_df = filtered_df[filtered_df['Worker'].isin(search_worker)]

    st.dataframe(filtered_df.sort_values(by="Timestamp", ascending=False), use_container_width=True)

    # B. DELETE ACCIDENTAL ENTRIES
    st.subheader("🗑️ Delete Incorrect Entry")
    with st.expander("Click here to remove a record"):
        if not filtered_df.empty:
            # Create a unique list of rows to delete
            delete_options = filtered_df['Timestamp'] + " | " + filtered_df['Job_Code'] + " | " + filtered_df['Activity']
            to_delete = st.selectbox("Select the exact record to delete", delete_options)
            
            if st.button("❌ Confirm Delete Forever"):
                # Remove the selected row from the main dataframe
                # We split back the string to find the exact match
                ts_del, job_del, act_del = to_delete.split(" | ")
                df_mngt = df_mngt[~((df_mngt['Timestamp'] == ts_del) & 
                                    (df_mngt['Job_Code'] == job_del) & 
                                    (df_mngt['Activity'] == act_del))]
                
                # Save & Sync
                df_mngt.to_csv(LOGS_FILE, index=False)
                sync_to_github(LOGS_FILE)
                st.error(f"Record for {job_del} deleted and synced.")
                st.rerun()

    # C. TOTAL PRODUCTION SUMMARIES
    st.subheader("📈 Production Totals")
    summary_type = st.radio("View Totals By:", ["Job Code", "Worker", "Activity"], horizontal=True)
    
    # Calculate Sums
    summary_df = df_mngt.groupby(summary_type).agg({'Output': 'sum', 'Hours': 'sum'}).reset_index()
    st.table(summary_df)

else:
    st.info("Start logging data to see summaries.")




