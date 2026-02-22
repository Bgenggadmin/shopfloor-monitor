import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. DATA FILES ---
WORKER_FILE = "bg_workers.txt"
JOB_FILE = "bg_jobs.txt"
LOG_FILE = "bg_production_log_v14.csv"

# Initialization
for file, default in [(WORKER_FILE, "Suresh,Ramesh"), (JOB_FILE, "JOB-101,DIST-05")]:
    if not os.path.exists(file):
        with open(file, "w") as f: f.write(default)

def get_list(filepath):
    with open(filepath, "r") as f:
        return [item.strip() for item in f.read().split(",") if item.strip()]

# --- 2. SECURITY ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 B&G Secure Access")
    pwd = st.text_input("Enter Password", type="password")
    if st.button("Log In"):
        if pwd == "BG2026": #
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("Invalid Password")
    st.stop()

# --- 3. MAIN INTERFACE ---
st.title("🏗️ B&G Engineering Industries")
tabs = st.tabs(["📝 Daily Entry", "📊 Analytics Dashboard", "⚙️ Admin Tools"])

# --- TAB 1: DAILY ENTRY ---
with tabs[0]:
    st.subheader("Shopfloor Production Log")
    
    # Prasanth, RamaSai, Subodth, Naresh, Ravindra are now added as loggers
    supervisors = ["Prasanth", "RamaSai", "Subodth", "Naresh", "Ravindra"]
    
    activity_map = {
        "Welder": ["Meters Weld"],
        "Fitter": ["Shell to Shell", "Top Dish Nozzle Fitup", "Rolling", "Marking", "Assembly"],
        "Buffer": ["Rough Polish", "Matt Finish", "Mirror Polish"],
        "Grinder": ["Grinding Work"],
        "Turner": ["Flange Machining", "Shaft Machining"],
        "Cutting": ["Plasma Cutting", "Gas Cutting"],
        "Driller": ["Hole Drilling"],
        "Other": ["Hydrotest", "Trial Run", "Pickling/Passivation"]
    }
    
    c1, c2 = st.columns(2)
    with c1:
        logged_by = st.selectbox("Logged By (Supervisor)", supervisors) # New field
        unit = st.selectbox("Unit", ["A", "B", "C"])
        worker = st.selectbox("Worker", get_list(WORKER_FILE))
        job = st.selectbox("Job Code", get_list(JOB_FILE))
    with c2:
        cat = st.selectbox("Category", list(activity_map.keys()))
        act = st.selectbox("Activity", activity_map[cat])
        hrs = st.number_input("Man-Hours Spent", min_value=0.0, step=0.5)
    
    out = st.number_input("Output Value (Meters/Qty)", min_value=0.0)
    rem = st.text_input("Remarks")

    if st.button("Submit to Backend"):
        now = datetime.now()
        row = f"{now.strftime('%Y-%m-%d')},{now.strftime('%H:%M')},{logged_by},{unit},{worker},{job},{cat},{act},{hrs},{out},{rem}\n"
        with open(LOG_FILE, "a") as f: f.write(row)
        st.success(f"Entry Saved by {logged_by}!")

# --- TAB 2: ANALYTICS ---
with tabs[1]:
    st.subheader("Business Performance Summaries")
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE, names=["Date","Time","Supervisor","Unit","Worker","Job","Category","Activity","Hours","Output","Remarks"])
        df['Date'] = pd.to_datetime(df['Date'])
        
        col_x, col_y = st.columns(2)
        with col_x:
            st.write("### 👥 Worker-wise Hours")
            st.bar_chart(df.groupby("Worker")["Hours"].sum())
        with col_y:
            st.write("### 📁 Job-wise Hours")
            st.bar_chart(df.groupby("Job")["Hours"].sum())
            
        st.write("### 👤 Entry-wise Loggers (Who logged how much)")
        st.bar_chart(df.groupby("Supervisor")["Hours"].count()) # Count of entries per supervisor
        
        with st.expander("View Detailed Raw Logs"):
            st.dataframe(df)
    else:
        st.info("No data logged yet.")

# --- TAB 3: ADMIN TOOLS ---
with tabs[2]:
    st.subheader("Manage Staff & Project Codes")
    colA, colB = st.columns(2)
    with colA:
        st.write("**Worker Management**")
        new_w = st.text_input("Add Worker Name")
        if st.button("Add Worker"):
            if new_w:
                with open(WORKER_FILE, "a") as f: f.write(f",{new_w}")
                st.rerun()
    with colB:
        st.write("**Job Management**")
        new_j = st.text_input("Add Job Code")
        if st.button("Create Job"):
            if new_j:
                with open(JOB_FILE, "a") as f: f.write(f",{new_j}")
                st.rerun()
