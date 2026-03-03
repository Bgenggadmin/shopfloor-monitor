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

# --- 2. DATA MIGRATION TOOL (Fixed Date/Time Parsing) ---
with st.expander("🛠️ OLD DATA IMPORT TOOL (Fixed Time/Date)"):
    st.write("This tool fixes your Date format (DD-MM-YYYY) to match the Cloud Database.")
    if st.button("🚀 Start Migration"):
        if os.path.exists("production_logs.csv"):
            try:
                # Load CSV
                old_df = pd.read_csv("production_logs.csv")
                
                # CLEANUP: Fix Blanks
                old_df['Output'] = old_df['Output'].fillna(0.0)
                old_df['Hours'] = old_df['Hours'].fillna(0.0)
                old_df['Notes'] = old_df['Notes'].fillna("")

                # DATE FIX: Convert '25-02-2026 10:03' to Database Format
                # We tell pandas exactly what your old format looks like: day-month-year hour:minute
                if 'Timestamp' in old_df.columns:
                    old_df['created_at'] = pd.to_datetime(old_df['Timestamp'], format='%d-%m-%Y %H:%M').dt.strftime('%Y-%m-%d %H:%M:%S')
                    old_df = old_df.drop(columns=['Timestamp'])

                data_to_import = old_df.to_dict(orient='records')
                
                # Upload
                batch_size = 50
                for i in range(0, len(data_to_import), batch_size):
                    batch = data_to_import[i:i + batch_size]
                    supabase.table("production").insert(batch).execute()
                
                st.success(f"✅ Migrated {len(data_to_import)} records with correct Date & Time!")
                st.rerun()
            except Exception as e:
                st.error(f"Migration Error: {e}")
        else:
            st.error("File 'production_logs.csv' not found.")

# --- 3. DATABASE LOADING ---
def load_data():
    try:
        # We fetch data sorted by created_at so newest is on top
        response = supabase.table("production").select("*").order("created_at", ascending=False).execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame(columns=["id", "created_at", "Supervisor", "Worker", "Job_Code", "Activity", "Unit", "Output", "Hours", "Notes"])
    except:
        return pd.DataFrame()

df = load_data()

# --- 4. PRODUCTION FORM ---
st.title("🏗️ B&G Production Master")

with st.form("production_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        # We populate these from session state or unique values in DB
        supervisors = sorted(df["Supervisor"].dropna().unique().tolist()) if not df.empty else ["RamaSai", "Ravindra"]
        supervisor = st.selectbox("Supervisor", ["-- Select --"] + supervisors)
        
        workers = sorted(df["Worker"].dropna().unique().tolist()) if not df.empty else []
        worker = st.selectbox("Worker Name", ["-- Select --"] + workers)
        
        jobs = sorted(df["Job_Code"].dropna().unique().tolist()) if not df.empty else []
        job_code = st.selectbox("Job Code", ["-- Select --"] + jobs)
        
        activities = ["Cutting (Plasma/Gas)", "Bending/Rolling", "Marking", "Fitting/Assembly", "Welding", "Grinding"]
        activity = st.selectbox("Activity", ["-- Select --"] + activities)
    
    with col2:
        unit = st.selectbox("Unit", ["Meters (Mts)", "Components (Nos)", "Layouts (Nos)", "Joints/Points (Nos)"])
        output = st.number_input("Output Value", min_value=0.0, step=0.1)
        hours = st.number_input("Hours Spent", min_value=0.0, step=0.5)
        notes = st.text_area("Notes")

    if st.form_submit_button("🚀 Log Production"):
        if any(v == "-- Select --" for v in [supervisor, worker, job_code, activity]):
            st.error("❌ Please select all fields.")
        else:
            # THIS CAPTURES BOTH CURRENT DATE AND TIME
            now_ist = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
            
            new_entry = {
                "created_at": now_ist,
                "Supervisor": supervisor, "Worker": worker, "Job_Code": job_code,
                "Activity": activity, "Unit": unit, "Output": float(output),
                "Hours": float(hours), "Notes": notes
            }
            supabase.table("production").insert(new_entry).execute()
            st.success("✅ Logged with Time!")
            st.rerun()

# --- 5. HISTORY & SUMMARY ---
st.divider()
if not df.empty:
    m1, m2 = st.columns(2)
    m1.metric("Total Hours", f"{df['Hours'].sum():.1f}")
    m2.metric("Entries Today", len(df))
    
    st.subheader("📋 Production History (Sorted by Time)")
    # Reformat for display to look nice: DD-MM-YYYY HH:MM
    display_df = df.copy()
    display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%d-%m-%Y %H:%M')
    display_df = display_df.rename(columns={'created_at': 'Timestamp'})
    
    st.dataframe(display_df.drop(columns=['id']), use_container_width=True)
