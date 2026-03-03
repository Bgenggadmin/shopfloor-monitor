import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import base64
from io import BytesIO
from supabase import create_client, Client

# --- 1. SETTINGS & CONNECTION ---
IST = pytz.timezone('Asia/Kolkata')
st.set_page_config(page_title="B&G Production Master", layout="wide", page_icon="🏗️")

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("❌ Database Connection Error. Check Streamlit Secrets.")
    st.stop()

# --- 2. DATABASE FUNCTIONS ---
def load_data():
    try:
        # Fetches newest data first
        response = supabase.table("production").select("*").order("created_at", desc=True).execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame(columns=["id", "created_at", "Supervisor", "Worker", "Job_Code", "Activity", "Unit", "Output", "Hours", "Notes"])
    except Exception:
        return pd.DataFrame()

df = load_data()

# --- 3. DYNAMIC DROPDOWN LOGIC ---
base_supervisors = ["RamaSai", "Ravindra", "Subodth", "Prasanth", "SUNIL"]
default_activities = ["Cutting (Plasma/Gas)", "CNC CUTTING", "Bending/Rolling", "Marking", "Fitting/Assembly", "Welding", "Grinding"]

if not df.empty:
    all_supervisors = sorted(list(set(base_supervisors + [s for s in df["Supervisor"].dropna().unique().tolist() if s not in ["N/A", ""]])))
    all_workers = sorted([w for w in df["Worker"].dropna().unique().tolist() if w not in ["N/A", ""]])
    all_jobs = sorted([j for j in df["Job_Code"].dropna().unique().tolist() if j not in ["N/A", ""]])
    db_activities = [a for a in df["Activity"].dropna().unique().tolist() if a not in ["N/A", ""]]
    all_activities = sorted(list(set(default_activities + db_activities)))
else:
    all_supervisors = sorted(base_supervisors)
    all_activities = sorted(default_activities)
    all_workers, all_jobs = [], []

# --- 4. NAVIGATION ---
st.sidebar.title("🛠️ Production Control")
menu = st.sidebar.radio("Go to:", ["🏗️ Production Entry", "🗂️ Manage Lists"])

# --- PAGE 1: PRODUCTION ENTRY ---
if menu == "🏗️ Production Entry":
    st.title("Daily Production Entry")
    
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            sup = st.selectbox("Supervisor", ["-- Select --"] + all_supervisors)
            wrk = st.selectbox("Worker Name", ["-- Select --"] + all_workers)
            jb = st.selectbox("Job Code", ["-- Select --"] + all_jobs)
            act = st.selectbox("Activity", ["-- Select --"] + all_activities)
        with col2:
            unt = st.selectbox("Unit", ["Meters (Mts)", "Components (Nos)", "Layouts (Nos)", "Joints/Points (Nos)"])
            out = st.number_input("Output Value", min_value=0.0)
            hrs = st.number_input("Hours Spent", min_value=0.0)
            nts = st.text_area("Notes")

        if st.form_submit_button("💾 Save to Cloud"):
            if "-- Select --" in [sup, wrk, jb, act]:
                st.warning("⚠️ Please select all fields.")
            else:
                payload = {
                    "created_at": datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'),
                    "Supervisor": sup, "Worker": wrk, "Job_Code": jb,
                    "Activity": act, "Unit": unt, "Output": float(out),
                    "Hours": float(hrs), "Notes": nts
                }
                supabase.table("production").insert(payload).execute()
                st.success("✅ Logged Successfully!")
                st.rerun()

    st.divider()
    
    # --- PRODUCTION HISTORY ---
    st.subheader("📋 Production History")
    if not df.empty:
        display_df = df[df['Notes'] != "SYSTEM_NEW_ITEM"].copy()
        if not display_df.empty:
            display_df['Date'] = pd.to_datetime(display_df['created_at']).dt.strftime('%d-%m-%Y')
            display_df['Time'] = pd.to_datetime(display_df['created_at']).dt.strftime('%H:%M')
            
            cols = ['id', 'Date', 'Time', 'Supervisor', 'Worker', 'Job_Code', 'Activity', 'Unit', 'Output', 'Hours', 'Notes']
            st.dataframe(display_df[cols], use_container_width=True)

            # --- EXPORT BUTTON ---
            csv = display_df[cols].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Production Report (CSV)",
                data=csv,
                file_name=f"B&G_Production_{datetime.now().strftime('%d-%m-%Y')}.csv",
                mime='text/csv',
            )
            
            # --- DELETE FEATURE ---
            st.divider()
            with st.expander("🗑️ Delete Incorrect Entry"):
                del_opts = display_df.apply(lambda x: f"ID: {x['id']} | {x['Job_Code']} | {x['Worker']}", axis=1).tolist()
                to_delete = st.selectbox("Select record to remove:", ["-- Select --"] + del_opts)
                if st.button("Confirm Delete"):
                    if to_delete != "-- Select --":
                        target_id = int(to_delete.split("|")[0].replace("ID: ", "").strip())
                        supabase.table("production").delete().eq("id", target_id).execute()
                        st.success(f"Record {target_id} deleted.")
                        st.rerun()

# --- PAGE 2: MANAGE LISTS ---
elif menu == "🗂️ Manage Lists":
    st.title("Manage Master Lists")
    st.info("Add new items here to update the dropdowns in the Production Entry form.")
    
    def add_item(col, val):
        payload = {
            "created_at": datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'), 
            "Supervisor": val if col == "Supervisor" else "N/A", 
            "Worker": val if col == "Worker" else "N/A", 
            "Job_Code": val if col == "Job_Code" else "N/A", 
            "Activity": val if col == "Activity" else "N/A", 
            "Unit": "N/A", "Output": 0, "Hours": 0, "Notes": "SYSTEM_NEW_ITEM"
        }
        supabase.table("production").insert(payload).execute()
        st.success(f"✅ '{val}' added to {col} list.")
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        new_w = st.text_input("New Worker Name")
        if st.button("Add Worker") and new_w: add_item("Worker", new_w)
        
        new_j = st.text_input("New Job Code")
        if st.button("Add Job") and new_j: add_item("Job_Code", new_j)
    
    with c2:
        new_act = st.text_input("New Activity")
        if st.button("Add Activity") and new_act: add_item("Activity", new_act)
        
        new_sup = st.text_input("New Supervisor")
        if st.button("Add Supervisor") and new_sup: add_item("Supervisor", new_sup)
