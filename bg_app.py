import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
from supabase import create_client, Client

# --- 1. SETTINGS & CONNECTION ---
IST = pytz.timezone('Asia/Kolkata')
st.set_page_config(page_title="B&G Production Master", layout="wide", page_icon="🏗️")

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("❌ Secrets missing! Add them in Streamlit Settings > Secrets.")
    st.stop()

# --- 2. DATA LOADING ---
def load_data():
    try:
        response = supabase.table("production").select("*").order("created_at", desc=True).execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame(columns=["id", "created_at", "Supervisor", "Worker", "Job_Code", "Activity", "Unit", "Output", "Hours", "Notes"])
    except Exception:
        return pd.DataFrame()

df = load_data()

# --- 3. DYNAMIC DROPDOWNS ---
# Fixed Master Lists
base_supervisors = ["RamaSai", "Ravindra", "Subodth", "Prasanth", "SUNIL"]
base_activities = ["Cutting (Plasma/Gas)", "CNC CUTTING", "Bending/Rolling", "Marking", "Fitting/Assembly", "Welding", "Grinding"]

# Combine base lists with anything found in Database records
if not df.empty:
    all_supervisors = sorted(list(set(base_supervisors + df["Supervisor"].dropna().unique().tolist())))
    all_workers = sorted(df["Worker"].dropna().unique().tolist())
    all_jobs = sorted(df["Job_Code"].dropna().unique().tolist())
else:
    all_supervisors = sorted(base_supervisors)
    all_workers = []
    all_jobs = []

# --- 4. MIGRATION TOOL (Stay minimized unless needed) ---
with st.expander("🛠️ DATA MIGRATION"):
    if st.button("🚀 Sync CSV to Cloud"):
        if os.path.exists("production_logs.csv"):
            try:
                old_df = pd.read_csv("production_logs.csv")
                old_df['Output'] = pd.to_numeric(old_df['Output'], errors='coerce').fillna(0.0)
                old_df['Hours'] = pd.to_numeric(old_df['Hours'], errors='coerce').fillna(0.0)
                old_df['Notes'] = old_df['Notes'].fillna("")
                if 'Timestamp' in old_df.columns:
                    old_df['created_at'] = pd.to_datetime(old_df['Timestamp'], dayfirst=True, format='mixed').dt.strftime('%Y-%m-%d %H:%M:%S')
                    old_df = old_df.drop(columns=['Timestamp'])
                supabase.table("production").insert(old_df.to_dict(orient='records')).execute()
                st.success("✅ Migrated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- 5. PRODUCTION FORM ---
st.title("🏗️ B&G Production Master")

with st.form("entry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        # DYNAMIC SUPERVISOR
        sel_sup = st.selectbox("Supervisor", ["-- Select --"] + all_supervisors + ["[+ Add New Supervisor]"])
        final_sup = sel_sup
        if sel_sup == "[+ Add New Supervisor]":
            final_sup = st.text_input("Enter New Supervisor Name")
            
        # DYNAMIC WORKER
        sel_wrk = st.selectbox("Worker Name", ["-- Select --"] + all_workers + ["[+ Add New Worker]"])
        final_wrk = sel_wrk
        if sel_wrk == "[+ Add New Worker]":
            final_wrk = st.text_input("Enter New Worker Name")
            
        # DYNAMIC JOB CODE
        sel_jb = st.selectbox("Job Code", ["-- Select --"] + all_jobs + ["[+ Add New Job Code]"])
        final_jb = sel_jb
        if sel_jb == "[+ Add New Job Code]":
            final_jb = st.text_input("Enter New Job Code (e.g. VST-1500)")
            
        act = st.selectbox("Activity", ["-- Select --"] + base_activities)

    with col2:
        unt = st.selectbox("Unit", ["Meters (Mts)", "Components (Nos)", "Layouts (Nos)", "Joints/Points (Nos)"])
        out = st.number_input("Output Value", min_value=0.0)
        hrs = st.number_input("Hours Spent", min_value=0.0)
        nts = st.text_area("Notes")

    if st.form_submit_button("💾 Save Production Log"):
        if "-- Select --" in [sel_sup, sel_wrk, sel_jb, act] or not final_sup or not final_wrk or not final_jb:
            st.warning("⚠️ Please fill all fields or enter new names.")
        else:
            payload = {
                "created_at": datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'),
                "Supervisor": final_sup, 
                "Worker": final_wrk, 
                "Job_Code": final_jb,
                "Activity": act, 
                "Unit": unt, 
                "Output": float(out),
                "Hours": float(hrs), 
                "Notes": nts
            }
            try:
                supabase.table("production").insert(payload).execute()
                st.success(f"✅ Record Saved! '{final_jb}' and '{final_sup}' updated in dropdowns.")
                st.rerun()
            except Exception as e:
                st.error(f"Sync Error: {e}")

# --- 6. SUMMARY & HISTORY ---
st.divider()
if not df.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Records", len(df))
    c2.metric("Total Hours", f"{df['Hours'].sum():.1f}")
    c3.metric("Active Jobs", df['Job_Code'].nunique())

    st.subheader("📋 Production History")
    display_df = df.copy()
    display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%d-%m-%Y %H:%M')
    st.dataframe(display_df.rename(columns={'created_at': 'Timestamp'}).drop(columns=['id']), use_container_width=True)
