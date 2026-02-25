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
    st.error("❌ GitHub Secrets missing in this repository!")
    st.stop()

st.set_page_config(page_title="B&G Production Master", layout="wide")
st.title("🏗️ B&G Production Master")

# --- 2. UTILITIES ---
def save_to_github(dataframe):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        csv_content = dataframe.to_csv(index=False)
        contents = repo.get_contents(DB_FILE)
        repo.update_file(contents.path, f"Prod Update {datetime.now(IST)}", csv_content, contents.sha)
        return True
    except Exception as e:
        st.error(f"GitHub Error: {e}")
        return False

if os.path.exists(DB_FILE):
    df = pd.read_csv(DB_FILE)
else:
    df = pd.DataFrame(columns=["Timestamp", "Supervisor", "Worker", "Job_Code", "Activity", "Unit", "Output", "Hours", "Notes"])

# --- 3. INPUT FORM ---
with st.form("production_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        supervisor = st.selectbox("Supervisor", ["RamaSai", "Ravindra", "Subodth"])
        worker = st.text_input("Worker Name")
        job_code = st.text_input("Job Code").upper()
        activity = st.selectbox("Activity", ["Cutting (Plasma/Gas)", "Bending/Rolling", "Marking", "Fitting/Assembly", "Welding", "Grinding"])
    
    with col2:
        unit = st.selectbox("Unit", ["Meters (Mts)", "Components (Nos)", "Layouts (Nos)", "Joints/Points (Nos)", "Amount/Length (Mts)"])
        output = st.number_input("Output Value", min_value=0.0, step=0.1)
        hours = st.number_input("Hours Spent", min_value=0.0, step=0.5)
        notes = st.text_area("Activity Details / Notes")

    if st.form_submit_button("🚀 Log Production Data"):
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
            "Supervisor": supervisor, "Worker": worker, "Job_Code": job_code,
            "Activity": activity, "Unit": unit, "Output": output,
            "Hours": hours, "Notes": notes
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        if save_to_github(df):
            st.success(f"✅ Data for {job_code} Logged!")
            st.rerun()

# --- 4. VIEW RECENT DATA ---
st.divider()
st.subheader("📋 Recent Production Logs")
st.dataframe(df.sort_values(by="Timestamp", ascending=False).head(20), use_container_width=True)
