import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. LOCAL STORAGE SETUP ---
DB_FILE = "production_logs.csv"

# Check for existing data
if os.path.exists(DB_FILE):
    df = pd.read_csv(DB_FILE)
else:
    df = pd.DataFrame(columns=["Timestamp", "Supervisor", "Worker", "Job_Code", "Hours", "Activity", "Status"])

st.title("🏭 B&G Production Log")

# --- 2. DATA BACKUP SECTION ---
# Use this to save to your local PC before updating GitHub code
with st.sidebar:
    st.header("💾 Backend Control")
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 DOWNLOAD TO EXCEL",
            data=csv,
            file_name=f"BG_Prod_Backup_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        if st.button("🗑️ Clear Backend Memory"):
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
                st.rerun()
    else:
        st.info("No logs saved yet.")

# --- 3. ENTRY FORM ---
with st.form("prod_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        supervisor = st.selectbox("Supervisor", ["Prasanth", "RamaSai", "Subodth"])
        worker = st.text_input("Worker Name")
        job = st.text_input("Job Code (e.g. SSR501)")
    with col2:
        hours = st.number_input("Hours Worked", min_value=0.0, step=0.5)
        activity = st.selectbox("Activity", ["Welding", "Fitup", "Grinding", "Marking"])
        status = st.radio("Status", ["In Progress", "Completed"])

    if st.form_submit_button("Submit to Backend"):
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "Supervisor": supervisor,
            "Worker": worker,
            "Job_Code": job,
            "Hours": hours,
            "Activity": activity,
            "Status": status
        }])
        
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        st.success(f"Log for {worker} saved locally!")
        st.balloons()

# --- 4. VIEW TABLE ---
st.divider()
st.subheader("📊 Recent Logs")
st.dataframe(df.sort_values(by="Timestamp", ascending=False), use_container_width=True)
