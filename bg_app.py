import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import base64
from github import Github
from io import BytesIO

# --- 1. SETUP ---
IST = pytz.timezone('Asia/Kolkata')
DB_FILE = "production_logs.csv"

try:
    REPO_NAME = st.secrets["GITHUB_REPO"]
    TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    st.error("❌ GitHub Secrets missing! Check your Streamlit Cloud settings.")
    st.stop()

st.set_page_config(page_title="B&G Production Master", layout="wide", page_icon="🏗️")
st.title("🏗️ B&G Production Master")

# --- 2. GITHUB UTILITIES ---
def save_to_github(dataframe):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        csv_content = dataframe.to_csv(index=False)
        contents = repo.get_contents(DB_FILE)
        repo.update_file(contents.path, f"Prod Sync {datetime.now(IST)}", csv_content, contents.sha)
        return True
    except Exception as e:
        st.error(f"⚠️ Sync Error: {e}")
        return False

# Load Data
if os.path.exists(DB_FILE):
    df = pd.read_csv(DB_FILE)
else:
    df = pd.DataFrame(columns=["Timestamp", "Supervisor", "Worker", "Job_Code", "Heat_No", "Activity", "Unit", "Output", "Hours", "Notes"])

# Get unique job codes for the dropdown
existing_jobs = sorted(df["Job_Code"].dropna().unique().tolist()) if not df.empty else []

# --- 3. INPUT FORM ---
with st.form("production_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        supervisor = st.selectbox("Supervisor", ["RamaSai", "Ravindra", "Subodth", "Prasanth"])
        worker = st.text_input("Worker Name")
        
        # --- THE SEARCHABLE DROPDOWN FIX ---
        if existing_jobs:
            job_selection = st.selectbox("Select Job Code", ["-- Search/Select --", "➕ Create New Job"] + existing_jobs)
            if job_selection == "➕ Create New Job":
                job_code = st.text_input("Enter New Job Code").upper()
            else:
                job_code = job_selection
        else:
            job_code = st.text_input("Job Code (e.g. 5KL_SSR_1507)").upper()
            
        heat_no = st.text_input("Heat No / Plate No").upper()
        activity = st.selectbox("Activity", [
            "Cutting (Plasma/Gas)", "Bending/Rolling", "Marking", 
            "Fitting/Assembly", "Welding", "Grinding", "Sand Blasting", "Painting"
        ])
    
    with col2:
        unit = st.selectbox("Unit", ["Meters (Mts)", "Components (Nos)", "Layouts (Nos)", "Joints/Points (Nos)", "Amount/Length (Mts)"])
        output = st.number_input("Output Value", min_value=0.0, step=0.1)
        hours = st.number_input("Hours Spent", min_value=0.0, step=0.5)
        notes = st.text_area("Activity Details / Consumables Used")

    if st.form_submit_button("🚀 Log Production & Sync"):
        if job_code in ["-- Search/Select --", ""] or not worker:
            st.warning("Please provide a Job Code and Worker Name.")
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
                st.success(f"✅ Production for {job_code} synced!")
                st.rerun()

# --- 4. VIEW RECENT LOGS ---
st.divider()
st.subheader("📋 Production History (Last 20 Entries)")
if not df.empty:
    display_df = df.sort_values(by="Timestamp", ascending=False).head(20)
    st.dataframe(display_df, use_container_width=True)
