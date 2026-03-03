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
default_activities = ["Cutting (Plasma/Gas)", "CNC CUTTING", "Bending/Rolling", "Marking", "Fitting/Assembly", "Welding", "Grinding"]

if not df.empty:
    all_supervisors = sorted(list(set(base_supervisors + df["Supervisor"].dropna().unique().tolist())))
    all_workers = sorted([w for w in df["Worker"].dropna().unique().tolist() if w not in ["N/A", ""]])
    all_jobs = sorted([j for j in df["Job_Code"].dropna().unique().tolist() if j not in ["N/A", ""]])
    db_activities = [a for a in df["Activity"].dropna().unique().tolist() if a not in ["N/A", ""]]
    all_activities = sorted(list(set(default_activities + db_activities)))
    
    all_supervisors = [s for s in all_supervisors if s not in ["N/A", ""]]
else:
    all_supervisors = sorted(base_supervisors)
    all_activities = sorted(default_activities)
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
            act = st.selectbox("Activity", ["-- Select --"] + all_activities)
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
    
    # --- RECENT LOGS TABLE ---
    st.subheader("📋 Production History")
    if not df.empty:
        display_df = df[df['Notes'] != "SYSTEM_NEW_ITEM"].copy()
        display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%d-%m-%Y %H:%M')
        display_df = display_df.rename(columns={'created_at': 'Timestamp', 'id': 'ID'})
        
        cols = ['ID', 'Timestamp', 'Supervisor', 'Worker', 'Job_Code', 'Activity', 'Unit', 'Output', 'Hours', 'Notes']
        st.dataframe(display_df[cols], use_container_width=True)

        # --- EXPORT TO CSV BUTTON ---
        csv = display_df[cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Production Ledger (CSV)",
            data=csv,
            file_name=f"Production_Report_{datetime.now().strftime('%d-%m-%Y')}.csv",
            mime='text/csv',
        )
        
        # DELETE SECTION
        st.markdown("### 🗑️ Delete an Entry")
        col_del1, col_del2 = st.columns([2, 1])
        with col_del1:
            delete_options = display_df.apply(lambda x: f"ID: {x['ID']} | Job: {x['Job_Code']} | Worker: {x['Worker']}", axis=1).tolist()
            to_delete = st.selectbox("Select entry to delete:", ["-- Select --"] + delete_options)
        
        with col_del2:
            st.write(" ") 
            if st.button("🗑️ Permanently Delete"):
                if to_delete != "-- Select --":
                    selected_id = int(to_delete.split("|")[0].replace("ID: ", "").strip())
                    supabase.table("production").delete().eq("id", selected_id).execute()
                    st.success(f"Entry {selected_id} deleted!")
                    st.rerun()

# --- PAGE 2: MANAGE LISTS ---
elif menu == "Manage Lists (Add New)":
    st.title("🗂️ Add New Items")
    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)
    
    with c1:
        new_s = st.text_input("New Supervisor")
        if st.button("Add Supervisor") and new_s:
            supabase.table("production").insert({"Supervisor": new_s, "Notes": "SYSTEM_NEW_ITEM", "Job_Code": "N/A", "Worker": "N/A", "Activity": "N/A"}).execute()
            st.success(f"Added {new_s}!"); st.rerun()
    with c2:
        new_j = st.text_input("New Job Code")
        if st.button("Add Job Code") and new_j:
            supabase.table("production").insert({"Job_Code": new_j, "Notes": "SYSTEM_NEW_ITEM", "Supervisor": "N/A", "Worker": "N/A", "Activity": "N/A"}).execute()
            st.success(f"Added {new_j}!"); st.rerun()
    with c3:
        new_w = st.text_input("New Worker")
        if st.button("Add Worker") and new_w:
            supabase.table("production").insert({"Worker": new_w, "Notes": "SYSTEM_NEW_ITEM", "Supervisor": "N/A", "Job_Code": "N/A", "Activity": "N/A"}).execute()
            st.success(f"Added {new_w}!"); st.rerun()
    with c4:
        new_act = st.text_input("New Activity")
        if st.button("Add Activity") and new_act:
            supabase.table("production").insert({"Activity": new_act, "Notes": "SYSTEM_NEW_ITEM", "Supervisor": "N/A", "Job_Code": "N/A", "Worker": "N/A"}).execute()
            st.success(f"Added {new_act}!"); st.rerun()

# --- PAGE 3: MIGRATION ---
elif menu == "Migration Tool":
    st.title("📂 Data Migration")
    if st.button("🚀 Run One-Time Migration"):
        if os.path.exists("production_logs.csv"):
            old_df = pd.read_csv("production_logs.csv")
            old_df['created_at'] = pd.to_datetime(old_df['Timestamp'], dayfirst=True, format='mixed').dt.strftime('%Y-%m-%d %H:%M:%S')
            old_df = old_df.drop(columns=['Timestamp']).fillna("")
            supabase.table("production").insert(old_df.to_dict(orient='records')).execute()
            st.success("Migration Successful!"); st.rerun()
