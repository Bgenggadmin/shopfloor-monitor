import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from supabase import create_client, Client

# --- 1. SETUP & CONNECTIONS ---
IST = pytz.timezone('Asia/Kolkata')

# Retrieve credentials from Streamlit Cloud Secrets
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("❌ Supabase Secrets missing! Add them in Streamlit Cloud Settings.")
    st.stop()

st.set_page_config(page_title="B&G Shopfloor Monitor", layout="wide", page_icon="🏗️")

# --- 2. DATABASE UTILITIES ---

def load_data_from_supabase():
    """Reads all records from the cloud database."""
    try:
        response = supabase.table("production").select("*").execute()
        if response.data:
            return pd.DataFrame(response.data)
        # Return empty df with required headers if no data yet
        return pd.DataFrame(columns=["id", "Timestamp", "Supervisor", "Worker", "Job_Code", "Activity", "Unit", "Output", "Hours", "Notes"])
    except Exception as e:
        st.error(f"Error loading cloud data: {e}")
        return pd.DataFrame()

def save_to_supabase(entry_dict):
    """Inserts a single log entry into the database."""
    try:
        supabase.table("production").insert(entry_dict).execute()
        return True
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return False

def delete_from_supabase(row_id):
    """Deletes a record by its unique ID."""
    try:
        supabase.table("production").delete().eq("id", row_id).execute()
        return True
    except Exception as e:
        st.error(f"Delete Error: {e}")
        return False

# --- 3. DYNAMIC DROPDOWNS ---
df = load_data_from_supabase()

# Initialize dropdown lists from existing data or defaults
if 'p_supervisors' not in st.session_state:
    st.session_state.p_supervisors = sorted(df["Supervisor"].dropna().unique().tolist()) if not df.empty else ["RamaSai", "Ravindra", "Subodth", "Prasanth"]
if 'p_workers' not in st.session_state:
    st.session_state.p_workers = sorted(df["Worker"].dropna().unique().tolist()) if not df.empty else []
if 'p_jobs' not in st.session_state:
    st.session_state.p_jobs = sorted(df["Job_Code"].dropna().unique().tolist()) if not df.empty else []

# --- 4. ADMIN CONTROLS ---
st.sidebar.header("⚙️ Admin Controls")
if not df.empty:
    st.sidebar.subheader("🗑️ Delete Mistake")
    # Show last 5 entries to allow quick correction
    last_entries_df = df.sort_values(by="id", ascending=False).head(5)
    delete_options = {f"ID {r['id']}: {r['Job_Code']}": r['id'] for _, r in last_entries_df.iterrows()}
    
    to_delete = st.sidebar.selectbox("Select entry", list(delete_options.keys()))
    if st.sidebar.button("Confirm Delete"):
        if delete_from_supabase(delete_options[to_delete]):
            st.sidebar.success("Removed!")
            st.rerun()

# --- 5. PRODUCTION FORM ---
st.title("🏗️ B&G Shopfloor Monitor")

with st.form("production_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        supervisor = st.selectbox("Supervisor", ["-- Select --"] + st.session_state.p_supervisors)
        worker = st.selectbox("Worker", ["-- Select --"] + st.session_state.p_workers)
        job_code = st.selectbox("Job Code", ["-- Select --"] + st.session_state.p_jobs)
    with c2:
        output = st.number_input("Output Value", min_value=0.0)
        hours = st.number_input("Hours Spent", min_value=0.0)
        notes = st.text_area("Notes / Consumables")

    if st.form_submit_button("🚀 Submit to Database"):
        if any(v == "-- Select --" for v in [supervisor, worker, job_code]):
            st.error("Please fill all required fields.")
        else:
            data = {
                "Timestamp": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
                "Supervisor": supervisor,
                "Worker": worker,
                "Job_Code": job_code,
                "Output": float(output),
                "Hours": float(hours),
                "Notes": notes
            }
            if save_to_supabase(data):
                st.success("Log Saved!")
                st.rerun()

# --- 6. LIVE VIEW ---
st.divider()
st.subheader("📋 Recent Logs")
if not df.empty:
    st.dataframe(df.sort_values(by="id", ascending=False).head(10), use_container_width=True)
