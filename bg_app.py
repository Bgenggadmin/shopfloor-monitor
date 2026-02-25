import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
from github import Github

# --- 1. SETUP ---
IST = pytz.timezone('Asia/Kolkata')
DB_FILE = "production_logs.csv"

try:
    REPO_NAME = st.secrets["GITHUB_REPO"]
    TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    st.error("❌ GitHub Secrets missing! Check Streamlit Cloud Settings.")
    st.stop()

st.set_page_config(page_title="B&G Production Master", layout="wide", page_icon="🏗️")
st.title("🏗️ B&G Production Master")

# --- 2. DATA UTILITIES ---
def save_to_github(dataframe):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        csv_content = dataframe.to_csv(index=False)
        contents = repo.get_contents(DB_FILE)
        repo.update_file(contents.path, f"Prod Update {datetime.now(IST)}", csv_content, contents.sha)
        return True
    except Exception as e:
        st.error(f"⚠️ Sync Error: {e}")
        return False

# Load Data
if os.path.exists(DB_FILE):
    df = pd.read_csv(DB_FILE)
else:
    df = pd.DataFrame(columns=["Timestamp", "Supervisor", "Worker", "Job_Code", "Heat_No", "Activity", "Unit", "Output", "Hours", "Notes"])

# --- 3. DYNAMIC LIST LOGIC ---
def get_list(column_name, default_list):
    if not df.empty and column_name in df.columns:
        found_items = df[column_name].dropna().unique().tolist()
        # Merge default items with what is in the CSV
        return sorted(list(set(default_list + [str(x) for x in found_items if str(x).strip() != ""])))
    return sorted(default_list)

# Load current lists
supervisors = get_list("Supervisor", ["RamaSai", "Ravindra", "Subodth", "Prasanth"])
workers = get_list("Worker", [])
jobs = get_list("Job_Code", [])
activities = get_list("Activity", ["Cutting (Plasma/Gas)", "Bending/Rolling", "Marking", "Fitting/Assembly", "Welding", "Grinding"])

# --- 4. INPUT FORM ---
with st.form("production_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        # SUPERVISOR
        s_sel = st.selectbox("Supervisor", ["-- Select Supervisor --", "➕ Add New"] + supervisors)
        supervisor = st.text_input("New Supervisor Name") if s_sel == "➕ Add New" else s_sel
        
        # WORKER
        w_sel = st.selectbox("Worker Name", ["-- Select Worker --", "➕ Add New"] + workers)
        worker = st.text_input("New Worker Name") if w_sel == "➕ Add New" else w_sel

        # JOB CODE
        j_sel = st.selectbox("Job Code", ["-- Select Job --", "➕ Add New"] + jobs)
        job_code = st.text_input("New Job Code").upper() if j_sel == "➕ Add New" else j_sel

    with col2:
        # ACTIVITY (Now Dynamic)
        a_sel = st.selectbox("Activity", ["-- Select Activity --", "➕ Add New Activity"] + activities)
        activity = st.text_input("New Activity Name") if a_sel == "➕ Add New Activity" else a_sel
        
        heat_no = st.text_input("Heat No / Plate No").upper()
        unit = st.selectbox("Unit", ["Meters (Mts)", "Components (Nos)", "Layouts (Nos)", "Joints/Points (Nos)", "Amount/Length (Mts)"])
        output = st.number_input("Output Value", min_value=0.0, step=0.1)
        hours = st.number_input("Hours Spent", min_value=0.0, step=0.5)

    notes = st.text_area("Activity Details / Consumables Used")

    if st.form_submit_button("🚀 Log Production & Sync"):
        # Validation
        invalid_selections = ["-- Select Supervisor --", "-- Select Worker --", "-- Select Job --", "-- Select Activity --", "", None]
        if any(v in invalid_selections for v in [supervisor, worker, job_code, activity]):
            st.error("❌ Please fill in all fields (Supervisor, Worker, Job, and Activity).")
        else:
            new_row = pd.DataFrame([{
                "Timestamp": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
                "Supervisor": supervisor, "Worker": worker, "Job_Code": job_code,
                "Heat_No": heat_no, "Activity": activity, "Unit": unit, 
                "Output": output, "Hours": hours, "Notes": notes
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DB_FILE, index=False)
            if save_to_github(df):
                st.success(f"✅ Success! {activity} for {job_code} saved.")
                st.rerun()

# --- 5. HISTORY ---
st.divider()
st.subheader("📋 Recent Production Logs")
if not df.empty:
    st.dataframe(df.sort_values(by="Timestamp", ascending=False).head(20), use_container_width=True)
