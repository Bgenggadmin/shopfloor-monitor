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

# --- 2. DATA MIGRATION TOOL (Smart Date Parsing) ---
with st.expander("🛠️ OLD DATA IMPORT TOOL (Smart Format Fix)"):
    st.write("This tool automatically detects and fixes your date formats.")
    if st.button("🚀 Start Migration"):
        if os.path.exists("production_logs.csv"):
            try:
                # 1. Load CSV
                old_df = pd.read_csv("production_logs.csv")
                
                # 2. CLEANUP: Fix Blanks/NaN
                old_df['Output'] = old_df['Output'].fillna(0.0)
                old_df['Hours'] = old_df['Hours'].fillna(0.0)
                old_df['Notes'] = old_df['Notes'].fillna("")

                # 3. DATE FIX: Use 'mixed' format to handle all variations
                if 'Timestamp' in old_df.columns:
                    # dayfirst=True ensures 02-03 is read as March 2nd, not Feb 3rd
                    old_df['created_at'] = pd.to_datetime(
                        old_df['Timestamp'], 
                        dayfirst=True, 
                        format='mixed'
                    ).dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    old_df = old_df.drop(columns=['Timestamp'])

                # 4. UPLOAD
                data_to_import = old_df.to_dict(orient='records')
                
                batch_size = 50
                for i in range(0, len(data_to_import), batch_size):
                    batch = data_to_import[i:i + batch_size]
                    supabase.table("production").insert(batch).execute()
                
                st.success(f"✅ Success! Migrated {len(data_to_import)} records.")
                st.balloons()
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
# --- 4. DATA LOADING & DROPDOWNS ---
df = load_data()

# 1. Supervisors: Start with your master list, then add any new ones found in DB
master_supervisors = ["RamaSai", "Ravindra", "Subodth", "Prasanth", "SUNIL"]
db_supervisors = df["Supervisor"].dropna().unique().tolist() if not df.empty else []
st.session_state.p_supervisors = sorted(list(set(master_supervisors + db_supervisors)))

# 2. Workers: Start empty and grow based on DB records
st.session_state.p_workers = sorted(df["Worker"].dropna().unique().tolist()) if not df.empty else []

# 3. Job Codes: Start empty and grow based on DB records
st.session_state.p_jobs = sorted(df["Job_Code"].dropna().unique().tolist()) if not df.empty else []

# 4. Activities: Hardcoded master list
st.session_state.p_activities = ["Cutting (Plasma/Gas)", "CNC CUTTING", "Bending/Rolling", "Marking", "Fitting/Assembly", "Welding", "Grinding"]

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


