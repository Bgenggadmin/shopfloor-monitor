import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
from supabase import create_client, Client

# --- 1. SETUP ---
IST = pytz.timezone('Asia/Kolkata')

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("❌ Secrets missing! Add SUPABASE_URL and SUPABASE_KEY to Settings > Secrets.")
    st.stop()

st.set_page_config(page_title="B&G Production Master", layout="wide", page_icon="🏗️")

# --- 2. DATA MIGRATION TOOL (Inside Expander) ---
with st.expander("🛠️ OLD DATA IMPORT TOOL (Run once)"):
    st.write("Click this to move your 'production_logs.csv' data to the cloud.")
    if st.button("🚀 Start Migration"):
        if os.path.exists("production_logs.csv"):
            old_df = pd.read_csv("production_logs.csv")
            # This fixes the "Timestamp" vs "created_at" error you saw
            # It renames the column to match Supabase's default
            old_df = old_df.rename(columns={'Timestamp': 'created_at'})
            data_to_import = old_df.to_dict(orient='records')
            try:
                supabase.table("production").insert(data_to_import).execute()
                st.success("✅ Old data successfully moved to Supabase!")
            except Exception as e:
                st.error(f"Migration Error: {e}. Check if column names in Supabase match the CSV.")
        else:
            st.error("File 'production_logs.csv' not found in GitHub.")

# --- 3. DATABASE FUNCTIONS ---
def load_data():
    try:
        response = supabase.table("production").select("*").execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame(columns=["id", "created_at", "Supervisor", "Worker", "Job_Code", "Activity", "Unit", "Output", "Hours", "Notes"])
    except:
        return pd.DataFrame()

# --- 4. DATA LOADING & DROPDOWNS ---
df = load_data()

if 'p_supervisors' not in st.session_state:
    st.session_state.p_supervisors = sorted(df["Supervisor"].dropna().unique().tolist()) if not df.empty else ["RamaSai", "Ravindra", "Subodth", "Prasanth"]
if 'p_workers' not in st.session_state:
    st.session_state.p_workers = sorted(df["Worker"].dropna().unique().tolist()) if not df.empty else []
if 'p_jobs' not in st.session_state:
    st.session_state.p_jobs = sorted(df["Job_Code"].dropna().unique().tolist()) if not df.empty else []
if 'p_activities' not in st.session_state:
    st.session_state.p_activities = sorted(df["Activity"].dropna().unique().tolist()) if not df.empty else ["Cutting (Plasma/Gas)", "Bending/Rolling", "Marking", "Fitting/Assembly", "Welding", "Grinding"]

# --- 5. PRODUCTION FORM ---
st.title("🏗️ B&G Production Master")

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
            st.error("❌ Please select valid options.")
        else:
            new_entry = {
                "created_at": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
                "Supervisor": supervisor,
                "Worker": worker,
                "Job_Code": job_code,
                "Activity": activity,
                "Unit": unit,
                "Output": float(output),
                "Hours": float(hours),
                "Notes": notes
            }
            try:
                supabase.table("production").insert(new_entry).execute()
                st.success("✅ Logged Successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- 6. SUMMARY & HISTORY ---
st.divider()
if not df.empty:
    m1, m2 = st.columns(2)
    m1.metric("Total Hours", f"{df['Hours'].sum():.1f}")
    m2.metric("Total Logs", len(df))
    st.subheader("📋 Recent Production Logs")
    # We use 'created_at' instead of 'Timestamp' to match Supabase
    st.dataframe(df.sort_values(by="id", ascending=False).head(20), use_container_width=True)
