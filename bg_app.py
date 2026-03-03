import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from supabase import create_client, Client

# --- 1. SETUP & CONNECTIONS ---
IST = pytz.timezone('Asia/Kolkata')

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("❌ Supabase Secrets missing! Check Streamlit Cloud Settings.")
    st.stop()

st.set_page_config(page_title="B&G Production Master", layout="wide", page_icon="🏗️")

# --- 2. DATA UTILITIES (Supabase) ---
def load_data():
    try:
        response = supabase.table("production").select("*").execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame(columns=["id", "Timestamp", "Supervisor", "Worker", "Job_Code", "Activity", "Unit", "Output", "Hours", "Notes"])
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def save_to_supabase(entry_dict):
    try:
        supabase.table("production").insert(entry_dict).execute()
        return True
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return False

def delete_from_supabase(row_id):
    try:
        supabase.table("production").delete().eq("id", row_id).execute()
        return True
    except Exception as e:
        st.error(f"Delete Error: {e}")
        return False

# --- 3. SESSION STATE FOR DYNAMIC DROPDOWNS ---
df = load_data()

if 'p_supervisors' not in st.session_state:
    st.session_state.p_supervisors = sorted(df["Supervisor"].dropna().unique().tolist()) if not df.empty else ["RamaSai", "Ravindra", "Subodth", "Prasanth"]
if 'p_workers' not in st.session_state:
    st.session_state.p_workers = sorted(df["Worker"].dropna().unique().tolist()) if not df.empty else []
if 'p_jobs' not in st.session_state:
    st.session_state.p_jobs = sorted(df["Job_Code"].dropna().unique().tolist()) if not df.empty else []
if 'p_activities' not in st.session_state:
    st.session_state.p_activities = sorted(df["Activity"].dropna().unique().tolist()) if not df.empty else ["Cutting (Plasma/Gas)", "Bending/Rolling", "Marking", "Fitting/Assembly", "Welding", "Grinding"]

# --- 4. ADMIN: DELETE LAST ENTRY ---
st.sidebar.header("⚙️ Admin Controls")
if not df.empty:
    st.sidebar.subheader("🗑️ Remove Mistake")
    # Show last 5 entries based on the DB ID
    last_entries_df = df.sort_values(by="id", ascending=False).head(5)
    delete_options = {f"ID {row['id']}: {row['Job_Code']} ({row['Activity']})": row['id'] for _, row in last_entries_df.iterrows()}
    
    to_delete = st.sidebar.selectbox("Select entry to delete", list(delete_options.keys()))
    
    if st.sidebar.button("Confirm Delete"):
        if delete_from_supabase(delete_options[to_delete]):
            st.sidebar.success("Entry Removed!")
            st.rerun()

# --- 5. THE "ADD NEW" SECTION ---
st.title("🏗️ B&G Production Master")

with st.expander("➕ ADD NEW OPTIONS (Supervisor / Worker / Job / Activity)"):
    c1, c2, c3, c4 = st.columns(4)
    
    ns = c1.text_input("New Supervisor")
    if c1.button("Add Supervisor"):
        if ns and ns not in st.session_state.p_supervisors:
            st.session_state.p_supervisors.append(ns)
            st.session_state.p_supervisors.sort()
            st.success(f"Added {ns}")

    nw = c2.text_input("New Worker")
    if c2.button("Add Worker"):
        if nw and nw not in st.session_state.p_workers:
            st.session_state.p_workers.append(nw)
            st.session_state.p_workers.sort()
            st.success(f"Added {nw}")

    nj = c3.text_input("New Job Code")
    if c3.button("Add Job"):
        if nj and nj not in st.session_state.p_jobs:
            st.session_state.p_jobs.append(nj.upper())
            st.session_state.p_jobs.sort()
            st.success(f"Added {nj}")

    na = c4.text_input("New Activity")
    if c4.button("Add Activity"):
        if na and na not in st.session_state.p_activities:
            st.session_state.p_activities.append(na)
            st.session_state.p_activities.sort()
            st.success(f"Added {na}")

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
            st.error("❌ Please select valid options from all dropdowns.")
        else:
            new_entry = {
                "Timestamp": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
                "Supervisor": supervisor,
                "Worker": worker,
                "Job_Code": job_code,
                "Activity": activity,
                "Unit": unit,
                "Output": float(output),
                "Hours": float(hours),
                "Notes": notes
            }
            
            if save_to_supabase(new_entry):
                st.success(f"✅ Data for {job_code} Logged to Supabase!")
                st.rerun()

# --- 7. HISTORY ---
st.divider()
st.subheader("📋 Recent Production Logs")
if not df.empty:
    # Sort by ID to show newest entries first
    st.dataframe(df.sort_values(by="id", ascending=False).head(20), use_container_width=True)
