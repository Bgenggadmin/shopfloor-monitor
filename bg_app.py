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

# --- 2. DATABASE FUNCTIONS ---
def load_data():
    try:
        # Fetching data sorted by time
        response = supabase.table("production").select("*").order("created_at", desc=True).execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame(columns=["id", "created_at", "Supervisor", "Worker", "Job_Code", "Activity", "Unit", "Output", "Hours", "Notes"])
    except Exception:
        return pd.DataFrame()

df = load_data()

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.title("🛠️ Admin Menu")
menu = st.sidebar.radio("Go to:", ["Production Entry", "Manage Lists (Add New)", "Migration Tool"])

# --- 4. DROPDOWN LOGIC ---
base_supervisors = ["RamaSai", "Ravindra", "Subodth", "Prasanth", "SUNIL"]
base_activities = ["Cutting (Plasma/Gas)", "CNC CUTTING", "Bending/Rolling", "Marking", "Fitting/Assembly", "Welding", "Grinding"]

if not df.empty:
    all_supervisors = sorted(list(set(base_supervisors + df["Supervisor"].dropna().unique().tolist())))
    all_workers = sorted(df["Worker"].dropna().unique().tolist())
    all_jobs = sorted(df["Job_Code"].dropna().unique().tolist())
    # Remove system placeholders from dropdowns
    all_workers = [w for w in all_workers if w != "N/A"]
    all_jobs = [j for j in all_jobs if j != "N/A"]
else:
    all_supervisors = sorted(base_supervisors)
    all_workers, all_jobs = [], []

# --- PAGE 1: PRODUCTION ENTRY ---
if menu == "Production Entry":
    st.title("🏗️ Production Entry")
    
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            sup = st.selectbox("Supervisor", ["-- Select --"] + all_supervisors)
            wrk = st.selectbox("Worker Name", ["-- Select --"] + all_workers)
            jb = st.selectbox("Job Code", ["-- Select --"] + all_jobs)
            act = st.selectbox("Activity", ["-- Select --"] + base_activities)
        with col2:
            unt = st.selectbox("Unit", ["Meters (Mts)", "Components (Nos)", "Layouts (Nos)", "Joints/Points (Nos)"])
            out = st.number_input("Output Value", min_value=0.0)
            hrs = st.number_input("Hours Spent", min_value=0.0)
            nts = st.text_area("Notes")

        if st.form_submit_button("💾 Save Production Log"):
            if "-- Select --" in [sup, wrk, jb, act]:
                st.warning("⚠️ Please fill all fields.")
            else:
                payload = {
                    "created_at": datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'),
                    "Supervisor": sup, "Worker": wrk, "Job_Code": jb,
                    "Activity": act, "Unit": unt, "Output": float(out),
                    "Hours": float(hrs), "Notes": nts
                }
                supabase.table("production").insert(payload).execute()
                st.success("✅ Logged!")
                st.rerun()

    st.divider()
    
    # --- RECENT LOGS TABLE (ALL FIELDS) ---
    st.subheader("📋 Recent Production History")
    if not df.empty:
        # Filter out system placeholders for the table view
        display_df = df[df['Notes'] != "SYSTEM_NEW_ITEM"].copy()
        
        # Formatting for readability
        display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%d-%m-%Y %H:%M')
        display_df = display_df.rename(columns={'created_at': 'Timestamp'})
        
        # Show the table
        st.dataframe(display_df.drop(columns=['id']), use_container_width=True)
        
        # DELETE SECTION
        with st.expander("🗑️ Delete Accidental Entries"):
            st.warning("Select an entry ID to delete it permanently.")
            delete_id = st.selectbox("Select ID to Delete", ["-- Select --"] + display_df['id'].tolist())
            if st.button("Confirm Delete"):
                if delete_id != "-- Select --":
                    supabase.table("production").delete().eq("id", delete_id).execute()
                    st.success(f"Entry {delete_id} deleted!")
                    st.rerun()

# --- PAGE 2: MANAGE LISTS ---
elif menu == "Manage Lists (Add New)":
    st.title("🗂️ Add New Items to Dropdowns")
    st.info("Added items will show up in the 'Production Entry' dropdowns immediately.")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        new_s = st.text_input("New Supervisor")
        if st.button("Add Supervisor") and new_s:
            supabase.table("production").insert({"Supervisor": new_s, "Notes": "SYSTEM_NEW_ITEM", "Job_Code": "N/A", "Worker": "N/A"}).execute()
            st.success(f"Added {new_s}!")
            st.rerun()

    with c2:
        new_j = st.text_input("New Job Code")
        if st.button("Add Job Code") and new_j:
            supabase.table("production").insert({"Job_Code": new_j, "Notes": "SYSTEM_NEW_ITEM", "Supervisor": "N/A", "Worker": "N/A"}).execute()
            st.success(f"Added {new_j}!")
            st.rerun()
            
    with c3:
        new_w = st.text_input("New Worker")
        if st.button("Add Worker") and new_w:
            supabase.table("production").insert({"Worker": new_w, "Notes": "SYSTEM_NEW_ITEM", "Supervisor": "N/A", "Job_Code": "N/A"}).execute()
            st.success(f"Added {new_w}!")
            st.rerun()

# --- PAGE 3: MIGRATION ---
elif menu == "Migration Tool":
    st.title("📂 Data Migration")
    if st.button("🚀 Run One-Time Migration"):
        if os.path.exists("production_logs.csv"):
            old_df = pd.read_csv("production_logs.csv")
            old_df['created_at'] = pd.to_datetime(old_df['Timestamp'], dayfirst=True, format='mixed').dt.strftime('%Y-%m-%d %H:%M:%S')
            old_df = old_df.drop(columns=['Timestamp']).fillna("")
            supabase.table("production").insert(old_df.to_dict(orient='records')).execute()
            st.success("Migration Successful!")
            st.rerun()
