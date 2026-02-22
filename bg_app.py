import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. DYNAMIC WORKER MANAGEMENT ---
# Using a local file to ensure worker lists persist across app restarts
WORKER_FILE = "bg_workers.txt"
if not os.path.exists(WORKER_FILE):
    with open(WORKER_FILE, "w") as f:
        f.write("Suresh,Ramesh,Kiran,Mehta")

def get_workers():
    with open(WORKER_FILE, "r") as f:
        content = f.read().strip()
        # Returns a clean list of names
        return [w.strip() for w in content.split(",") if w.strip()]

# --- 2. MASTER DATA CONFIGURATION ---
valid_units = ["A", "B", "C"]
# Critical for your estimation team to track project-specific costs
valid_jobs = ["JOB-101", "DIST-05", "VESSEL-02", "REACTOR-01"]

# High-precision activity mapping for pharma-grade fabrication
activity_map = {
    "Welder": ["Meters Weld"],
    "Fitter": ["Shell to Shell", "Top Dish Nozzle Fitup", "Rolling", "Marking", "Assembly"],
    "Buffer": ["Rough Polish", "Matt Finish", "Mirror Polish"],
    "Grinder": ["Grinding Work"],
    "Turner": ["Flange Machining", "Shaft Machining", "General Machining"],
    "Cutting": ["Plasma Cutting", "Gas Cutting", "Shearing"],
    "Driller": ["Hole Drilling"],
    "Other Works": ["Hydrotest", "Trial Run", "Pickling/Passivation", "Maintenance"]
}

# --- 3. SECURITY & AUTHENTICATION ---
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔐 B&G Secure Access")
        pwd = st.text_input("Enter Shopfloor Password", type="password")
        if st.button("Log In"):
            if pwd == "BG2026": # Your standard Monday launch password
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Invalid Password")
        return False
    return True

# --- 4. MAIN APPLICATION ---
if check_auth():
    st.title("🏗️ B&G Engineering: Shopfloor Monitor")

    # --- SIDEBAR: NAVIGATION & ADMIN TOOLS ---
    st.sidebar.header("Navigation")
    selected_unit = st.sidebar.selectbox("Current Unit", valid_units)
    filter_date = st.sidebar.date_input("View Records For", datetime.now())
    
    # Organized Admin Section to prevent display issues
    with st.sidebar.expander("⚙️ Admin: Staff Management", expanded=False):
        st.subheader("➕ Add New Staff")
        add_name = st.text_input("New Worker Name")
        if st.button("Register Worker"):
            workers = get_workers()
            if add_name and add_name not in workers:
                with open(WORKER_FILE, "a") as f:
                    f.write(f",{add_name}")
                st.success(f"Added {add_name}!")
                st.rerun()

        st.divider()

        st.subheader("🗑️ Remove Staff")
        current_staff = get_workers()
        rem_name = st.selectbox("Select Staff to Remove", current_staff)
        if st.button("Delete Worker"):
            if len(current_staff) > 1:
                current_staff.remove(rem_name)
                with open(WORKER_FILE, "w") as f:
                    f.write(",".join(current_staff))
                st.warning(f"Removed {rem_name}")
                st.rerun()
            else:
                st.error("Cannot delete the last worker.")

    # --- 5. DATA ENTRY SECTION ---
    st.subheader(f"Log Entry: Unit {selected_unit}")
    c1, c2 = st.columns(2)
    
    with c1:
        worker = st.selectbox("Worker Name", get_workers())
        category = st.selectbox("Work Category", list(activity_map.keys()))
        activity = st.selectbox("Specific Activity", activity_map[category])
        job = st.selectbox("Job Code", valid_jobs)
    
    with c2:
        # Essential for your Estimation Team
        hours = st.number_input("Man-Hours Spent", min_value=0.0, step=0.5)
        
        # Dynamic Measurement Labels
        if category == "Welder": uom = "Meters"
        elif category == "Buffer": uom = "Sq. Ft"
        elif category == "Driller": uom = "No. of Holes"
        elif category in ["Grinder", "Cutting"]: uom = "Meters"
        else: uom = "Qty/Progress %"
            
        output = st.number_input(f"Output ({uom})", min_value=0.0, step=0.1)

    remarks = st.text_input("Remarks (Efficiency bottlenecks/notes)")

    if st.button("Submit to Backend"):
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%H:%M")
        
        # Row structure: Date, Time, Unit, Worker, Category, Activity, Job, Hours, Output, Remarks
        row = f"{date_str},{time_str},{selected_unit},{worker},{category},{activity},{job},{hours},{output},{remarks}\n"
        
        # Saving to the versioned CSV log
        with open("bg_production_log_v11.csv", "a") as f:
            f.write(row)
        st.success(f"Entry Recorded for {selected_unit}!")

    # --- 6. EFFICIENCY DASHBOARD ---
    st.divider()
    if os.path.exists("bg_production_log_v11.csv"):
        cols = ["Date","Time","Unit","Worker","Category","Activity","Job","Hours","Output","Remarks"]
        df = pd.read_csv("bg_production_log_v11.csv", names=cols)
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        
        # Job-wise Man-Hour Accumulation to improve delivery efficiency
        st.subheader("📊 Job-wise Man-Hour Accumulation")
        job_summary = df.groupby("Job")["Hours"].sum()
        st.bar_chart(job_summary)
        
        st.write(f"Today's Activity Log (Unit {selected_unit}):")
        display_df = df[(df['Date'] == filter_date) & (df['Unit'] == selected_unit)]
        st.dataframe(display_df, use_container_width=True)