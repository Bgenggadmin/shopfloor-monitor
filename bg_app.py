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
    st.error("❌ Secrets missing! Check Streamlit Cloud Settings.")
    st.stop()

st.set_page_config(page_title="B&G Production Master", layout="wide", page_icon="🏗️")

# --- 2. DATA UTILITIES ---
def save_to_github(dataframe):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        csv_content = dataframe.to_csv(index=False)
        contents = repo.get_contents(DB_FILE)
        repo.update_file(contents.path, f"Prod Sync {datetime.now(IST)}", csv_content, contents.sha)
        return True
    except: return False

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Timestamp", "Supervisor", "Worker", "Job_Code", "Activity", "Unit", "Output", "Hours", "Notes"])

# --- 3. SESSION STATE FOR DYNAMIC DROPDOWNS ---
df = load_data()

# Initialize dropdown lists in session state so buttons can update them instantly
if 'p_supervisors' not in st.session_state:
    st.session_state.p_supervisors = sorted(df["Supervisor"].dropna().unique().tolist()) if not df.empty else ["RamaSai", "Ravindra", "Subodth", "Prasanth"]
if 'p_workers' not in st.session_state:
    st.session_state.p_workers = sorted(df["Worker"].dropna().unique().tolist()) if not df.empty else []
if 'p_jobs' not in st.session_state:
    st.session_state.p_jobs = sorted(df["Job_Code"].dropna().unique().tolist()) if not df.empty else []
if 'p_activities' not in st.session_state:
    st.session_state.p_activities = sorted(df["Activity"].dropna().unique().tolist()) if not df.empty else ["Cutting (Plasma/Gas)", "Bending/Rolling", "Marking", "Fitting/Assembly", "Welding", "Grinding"]

# --- 4. THE "ADD NEW" SECTION ---
st.title("🏗️ B&G Production Master")

with st.expander("➕ ADD NEW OPTIONS (Supervisor / Worker / Job / Activity)"):
    c1, c2, c3, c4 = st.columns(4)
    
    # Add Supervisor
    ns = c1.text_input("New Supervisor")
    if c1.button("Add Supervisor"):
        if ns and ns not in st.session_state.p_supervisors:
            st.session_state.p_supervisors.append(ns)
            st.session_state.p_supervisors.sort()
            st.success(f"Added {ns}")

    # Add Worker
    nw = c2.text_input("New Worker")
    if c2.button("Add Worker"):
        if nw and nw not in st.session_state.p_workers:
            st.session_state.p_workers.append(nw)
            st.session_state.p_workers.sort()
            st.success(f"Added {nw}")

    # Add Job
    nj = c3.text_input("New Job Code")
    if c3.button("Add Job"):
        if nj and nj not in st.session_state.p_jobs:
            st.session_state.p_jobs.append(nj.upper())
            st.session_state.p_jobs.sort()
            st.success(f"Added {nj}")

    # Add Activity
    na = c4.text_input("New Activity")
    if c4.button("Add Activity"):
        if na and na not in st.session_state.p_activities:
            st.session_state.p_activities.append(na)
            st.session_state.p_activities.sort()
            st.success(f"Added {na}")

st.divider()

# --- 5. MAIN PRODUCTION FORM ---
with st.form("production_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        supervisor = st.selectbox("Supervisor", ["-- Select --"] + st.session_state.p_supervisors)
        worker = st.selectbox("Worker Name", ["-- Select --"] + st.session_state.p_workers)
        job_code = st.selectbox("Job Code", ["-- Select --"] + st.session_state.p_jobs)
        activity = st.selectbox("Activity", ["-- Select --"] + st.session_state.p_activities)
    
    with col2:
        unit = st.selectbox("Unit", ["Meters (Mts)", "Components (Nos)", "Layouts (Nos)", "Joints/Points (Nos)", "Amount/Length (Mts)"])
        output = st.number_input("Output Value", min_value=0.0, step=0.1)
        hours = st.number_input("Hours Spent", min_value=0.0, step=0.5)
        notes = st.text_area("Activity Details / Consumables Used")

    if st.form_submit_button("🚀 Log Production & Sync"):
        if any(v == "-- Select --" for v in [supervisor, worker, job_code, activity]):
            st.error("❌ Please select valid options from all dropdowns.")
        else:
            new_row = pd.DataFrame([{
                "Timestamp": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
                "Supervisor": supervisor, "Worker": worker, "Job_Code": job_code,
                "Activity": activity, "Unit": unit, "Output": output, 
                "Hours": hours, "Notes": notes
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DB_FILE, index=False)
            if save_to_github(df):
                st.success(f"✅ Production for {job_code} logged!")
                st.rerun()

# --- 6. HISTORY ---
st.divider()
st.subheader("📋 Recent Production Logs")
if not df.empty:
    st.dataframe(df.sort_values(by="Timestamp", ascending=False).head(20), use_container_width=True)
