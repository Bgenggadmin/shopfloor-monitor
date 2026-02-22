import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. DYNAMIC DATA MANAGEMENT ---
WORKER_FILE = "bg_workers.txt"
JOB_FILE = "bg_jobs.txt"

# Initialize files if they don't exist
for file, default in [(WORKER_FILE, "Suresh,Ramesh,Kiran"), (JOB_FILE, "JOB-101,DIST-05,VESSEL-02")]:
    if not os.path.exists(file):
        with open(file, "w") as f: f.write(default)

def get_list(filepath):
    with open(filepath, "r") as f:
        return [item.strip() for item in f.read().split(",") if item.strip()]

# --- 2. SECURITY ---
def check_auth():
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
        return False
    return True

if check_auth():
    st.title("🏗️ B&G Engineering: Shopfloor Monitor")

    # SIDEBAR: NAVIGATION & ADMIN
    st.sidebar.header("Navigation")
    selected_unit = st.sidebar.selectbox("Current Unit", ["A", "B", "C"])
    filter_date = st.sidebar.date_input("View Records For", datetime.now())

    # --- ADMIN DRAWER: STAFF & JOBS ---
    with st.sidebar.expander("⚙️ Admin: Manage Staff & Jobs"):
        # Staff Management
        st.subheader("👥 Workers")
        new_w = st.text_input("Add Worker")
        if st.button("Add Worker"):
            if new_w and new_w not in get_list(WORKER_FILE):
                with open(WORKER_FILE, "a") as f: f.write(f",{new_w}")
                st.rerun()
        
        rem_w = st.selectbox("Remove Worker", get_list(WORKER_FILE))
        if st.button("Delete Worker"):
            w_list = get_list(WORKER_FILE)
            if len(w_list) > 1:
                w_list.remove(rem_w)
                with open(WORKER_FILE, "w") as f: f.write(",".join(w_list))
                st.rerun()

        st.divider()

        # Job Management (The New Feature)
        st.subheader("📁 Job Codes")
        new_j = st.text_input("Add New Job Code")
        if st.button("Add Job"):
            if new_j and new_j not in get_list(JOB_FILE):
                with open(JOB_FILE, "a") as f: f.write(f",{new_j}")
                st.rerun()
        
        rem_j = st.selectbox("Remove Old Job", get_list(JOB_FILE))
        if st.button("Delete Job Code"):
            j_list = get_list(JOB_FILE)
            if len(j_list) > 1:
                j_list.remove(rem_j)
                with open(JOB_FILE, "w") as f: f.write(",".join(j_list))
                st.rerun()

    # --- 3. DATA ENTRY ---
    activity_map = {
        "Welder": ["Meters Weld"],
        "Fitter": ["Shell to Shell", "Top Dish Nozzle Fitup", "Rolling", "Marking", "Assembly"],
        "Buffer": ["Rough Polish", "Matt Finish", "Mirror Polish"],
        "Grinder": ["Grinding Work"],
        "Turner": ["Flange Machining", "Shaft Machining", "General Machining"],
        "Cutting": ["Plasma Cutting", "Gas Cutting", "Shearing"],
        "Driller": ["Hole Drilling"],
        "Other Works": ["Hydrotest", "Trial Run", "Pickling/Passivation"]
    }

    st.subheader(f"Log Entry: Unit {selected_unit}")
    c1, c2 = st.columns(2)
    with c1:
        worker = st.selectbox("Worker", get_list(WORKER_FILE))
        category = st.selectbox("Category", list(activity_map.keys()))
        activity = st.selectbox("Activity", activity_map[category])
        job = st.selectbox("Job Code", get_list(JOB_FILE)) # Now Dynamic!
    with c2:
        hours = st.number_input("Man-Hours Spent", min_value=0.0, step=0.5)
        output = st.number_input("Output Value", min_value=0.0, step=0.1)

    remarks = st.text_input("Remarks")

    if st.button("Submit to Backend"):
        date_str = datetime.now().strftime("%Y-%m-%d")
        row = f"{date_str},{selected_unit},{worker},{category},{activity},{job},{hours},{output},{remarks}\n"
        with open("bg_production_log_v12.csv", "a") as f: f.write(row)
        st.success("Entry Recorded!")
