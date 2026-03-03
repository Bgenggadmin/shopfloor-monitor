import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
from supabase import create_client, Client

# --- 1. SETTINGS & CONNECTION ---
IST = pytz.timezone('Asia/Kolkata')

# Page Config
st.set_page_config(page_title="B&G Production Master", layout="wide", page_icon="🏗️")

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("❌ Secrets missing! Please add SUPABASE_URL and SUPABASE_KEY in Streamlit Settings > Secrets.")
    st.stop()

# --- 2. DATA LOADING FUNCTION ---
def load_data():
    try:
        # Fetch data sorted by time so newest is always at the top
        response = supabase.table("production").select("*").order("created_at", ascending=False).execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame(columns=["id", "created_at", "Supervisor", "Worker", "Job_Code", "Activity", "Unit", "Output", "Hours", "Notes"])
    except Exception as e:
        st.error(f"Database Error: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. MASTER DROPDOWN LISTS ---
# These lists stay even if the database is empty
master_supervisors = ["RamaSai", "Ravindra", "Subodth", "Prasanth", "SUNIL"]
master_activities = ["Cutting (Plasma/Gas)", "CNC CUTTING", "Bending/Rolling", "Marking", "Fitting/Assembly", "Welding", "Grinding"]

# These lists grow automatically based on what has been entered in the past
db_workers = sorted(df["Worker"].dropna().unique().tolist()) if not df.empty else []
db_jobs = sorted(df["Job_Code"].dropna().unique().tolist()) if not df.empty else []

# --- 4. DATA MIGRATION TOOL (Admin Section) ---
with st.expander("🛠️ DATA MIGRATION (Move CSV to Cloud)"):
    st.info("Use this to move old records from production_logs.csv into the new system.")
    if st.button("🚀 Start Migration Now"):
        if os.path.exists("production_logs.csv"):
            try:
                old_df = pd.read_csv("production_logs.csv")
                
                # Fill empty values to prevent JSON errors
                old_df['Output'] = old_df['Output'].fillna(0.0)
                old_df['Hours'] = old_df['Hours'].fillna(0.0)
                old_df['Notes'] = old_df['Notes'].fillna("")

                # Fix Date Format: Convert DD-MM-YYYY to YYYY-MM-DD
                if 'Timestamp' in old_df.columns:
                    old_df['created_at'] = pd.to_datetime(
                        old_df['Timestamp'], dayfirst=True, format='mixed'
                    ).dt.strftime('%Y-%m-%d %H:%M:%S')
                    old_df = old_df.drop(columns=['Timestamp'])

                data_records = old_df.to_dict(orient='records')
                
                # Upload in batches of 50
                for i in range(0, len(data_records), 50):
                    batch = data_records[i:i + 50]
                    supabase.table("production").insert(batch).execute()
                
                st.success(f"✅ Successfully migrated {len(data_records)} records!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Migration failed: {e}")
        else:
            st.error("Could not find 'production_logs.csv' in the main folder.")

# --- 5. MAIN UI & FORM ---
st.title("🏗️ B&G Production Master")

# Top Summary Metrics
if not df.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Logs", len(df))
    m2.metric("Total Man-Hours", f"{df['Hours'].sum():.1f} Hrs")
    m3.metric("Unique Jobs", df['Job_Code'].nunique())

st.divider()

# Production Entry Form
with st.form("entry_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    
    with c1:
        sup = st.selectbox("Supervisor", ["-- Select --"] + master_supervisors)
        # Use existing workers + option to type new
        wrk = st.selectbox("Worker Name", ["-- Select --"] + db_workers + ["[ADD NEW]"])
        if wrk == "[ADD NEW]":
            wrk = st.text_input("Enter New Worker Name")
            
        jb = st.selectbox("Job Code", ["-- Select --"] + db_jobs + ["[ADD NEW]"])
        if jb == "[ADD NEW]":
            jb = st.text_input("Enter New Job Code")
            
        act = st.selectbox("Activity", ["-- Select --"] + master_activities)

    with c2:
        unt = st.selectbox("Unit", ["Meters (Mts)", "Components (Nos)", "Layouts (Nos)", "Joints/Points (Nos)", "Amount/Length (Mts)"])
        out = st.number_input("Output Value", min_value=0.0, step=0.1)
        hrs = st.number_input("Hours Spent", min_value=0.0, step=0.5)
        nts = st.text_area("Notes / Activity Details")

    if st.form_submit_button("💾 Save Production Log"):
        if any(x in ["-- Select --", "", None] for x in [sup, wrk, jb, act]):
            st.warning("⚠️ Please fill in all required fields.")
        else:
            new_log = {
                "created_at": datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'),
                "Supervisor": sup,
                "Worker": wrk,
                "Job_Code": jb,
                "Activity": act,
                "Unit": unt,
                "Output": float(out),
                "Hours": float(hrs),
                "Notes": nts
            }
            try:
                supabase.table("production").insert(new_log).execute()
                st.success("✅ Logged to Cloud!")
                st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")

# --- 6. HISTORY TABLE ---
st.subheader("📋 Recent Production History")
if not df.empty:
    # Formatting for display: Convert back to DD-MM-YYYY
    display_df = df.copy()
    display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%d-%m-%Y %H:%M')
    display_df = display_df.rename(columns={'created_at': 'Timestamp'})
    
    # Hide the ID column from the user
    st.dataframe(display_df.drop(columns=['id']), use_container_width=True)
else:
    st.info("No data found in the cloud yet. Try running the Migration tool above.")
