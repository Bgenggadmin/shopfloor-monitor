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

# --- 2. DATA MIGRATION TOOL (With Time & NaN Fix) ---
with st.expander("🛠️ OLD DATA IMPORT TOOL"):
    st.write("Click this to move your 'production_logs.csv' data to Supabase.")
    if st.button("🚀 Start Migration"):
        if os.path.exists("production_logs.csv"):
            try:
                old_df = pd.read_csv("production_logs.csv")
                
                # CLEANUP: Fix blanks/NaN so they don't crash JSON
                old_df['Output'] = old_df['Output'].fillna(0.0)
                old_df['Hours'] = old_df['Hours'].fillna(0.0)
                old_df['Notes'] = old_df['Notes'].fillna("")
                
                # TIME FIX: Map CSV 'Timestamp' to Supabase 'created_at'
                if 'Timestamp' in old_df.columns:
                    old_df = old_df.rename(columns={'Timestamp': 'created_at'})
                
                data_to_import = old_df.to_dict(orient='records')
                
                # Upload in batches
                batch_size = 50
                for i in range(0, len(data_to_import), batch_size):
                    batch = data_to_import[i:i + batch_size]
                    supabase.table("production").insert(batch).execute()
                
                st.success(f"✅ Migrated {len(data_to_import)} records with original timestamps!")
                st.rerun()
            except Exception as e:
                st.error(f"Migration Error: {e}")
        else:
            st.error("File 'production_logs.csv' not found.")

# --- 3. DATABASE LOADING ---
def load_data():
    try:
        response = supabase.table("production").select("*").execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame(columns=["id", "created_at", "Supervisor", "Worker", "Job_Code", "Activity", "Unit", "Output", "Hours", "Notes"])
    except:
        return pd.DataFrame()

df = load_data()

# --- 4. DYNAMIC DROPDOWNS ---
if 'p_supervisors' not in st.session_state:
    st.session_state.p_supervisors = sorted(df["Supervisor"].dropna().unique().tolist()) if not df.empty else ["RamaSai", "Ravindra", "Subodth", "Prasanth"]
if 'p_workers' not in st.session_state:
    st.session_state.p_workers = sorted(df["Worker"].dropna().unique().tolist()) if not df.empty else []
if 'p_jobs' not in st.session_state:
    st.session_state.p_jobs = sorted(df["Job_Code"].dropna().unique().tolist()) if not df.empty else []
if 'p_activities' not in st.session_state:
    st.session_state.p_activities = sorted(df["Activity"].dropna().unique().tolist()) if not df.empty else ["Cutting (Plasma/Gas)", "Bending/Rolling", "Marking", "Fitting/Assembly", "Welding", "Grinding"]

# --- 5. LOG SUMMARY SECTION ---
st.title("🏗️ B&G Production Master")
if not df.empty:
    st.subheader("📊 Production Summary")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Total Logs", len(df))
    with s2:
        st.metric("Total Hours Spent", f"{df['Hours'].sum():.1f} Hrs")
    with s3:
        st.metric("Active Job Codes", df['Job_Code'].nunique())
    with s4:
        st.metric("Unique Workers", df['Worker'].nunique())
st.divider()

# --- 6. MAIN PRODUCTION FORM ---
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
                "Supervisor": supervisor, "Worker": worker, "Job_Code": job_code,
                "Activity": activity, "Unit": unit, "Output": float(output),
                "Hours": float(hours), "Notes": notes
            }
            try:
                supabase.table("production").insert(new_entry).execute()
                st.success("✅ Logged Successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Sync Error: {e}")

# --- 7. HISTORY ---
st.subheader("📋 Recent Production Logs")
if not df.empty:
    # Rename 'created_at' back to 'Timestamp' for display so it looks like the old app
    display_df = df.rename(columns={'created_at': 'Timestamp'})
    st.dataframe(display_df.sort_values(by="id", ascending=False).head(30), use_container_width=True)
