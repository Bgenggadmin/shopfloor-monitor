import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
from github import Github

# --- 1. SETUP & TIMEZONE (IST) ---
IST = pytz.timezone('Asia/Kolkata')
LOGS_FILE = "production_logs.csv"
WORKERS_FILE = "workers.txt"
JOBS_FILE = "jobs.txt"

UNITS = {
    "Welding": "Meters (Mts)", "Grinding": "Amount/Length (Mts)", 
    "Drilling": "Quantity (Nos)", "Cutting (Plasma/Gas)": "Meters (Mts)",
    "Fitting/Assembly": "Joints/Points (Nos)", "Marking": "Layouts (Nos)",
    "Buffing/Polishing": "Square Feet (Sq Ft)", "Bending/Rolling": "Components (Nos)",
    "Hydro-Testing": "Equipment (Nos)", "Painting/Coating": "Square Meters (Sq M)",
    "Dispatch/Loading": "Weight (Tons/Kgs)"
}

HEADERS = ["Timestamp", "Supervisor", "Worker", "Job_Code", "Activity", "Unit", "Output", "Hours", "Notes"]

# --- 2. GITHUB SYNC ---
def sync_to_github(file_path):
    try:
        if "GITHUB_TOKEN" in st.secrets:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["GITHUB_REPO"])
            with open(file_path, "r") as f:
                content = f.read()
            try:
                contents = repo.get_contents(file_path)
                repo.update_file(contents.path, f"Sync {datetime.now(IST)}", content, contents.sha)
            except:
                repo.create_file(file_path, "Initial Create", content)
    except Exception as e:
        st.error(f"Sync Error: {e}")

def load_list(file_path, defaults):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return defaults

st.set_page_config(page_title="B&G Production", layout="wide")
st.title("🏗️ B&G Production & Progress Tracker")

workers = load_list(WORKERS_FILE, ["Prasanth", "RamaSai", "Subodth", "Sunil", "Naresh", "Ravindra"])
job_list = load_list(JOBS_FILE, ["SSR501", "SSR502", "VESSEL-101"])

# --- 3. ENTRY FORM (FIXED LIVE UNIT UPDATING) ---
# Use columns OUTSIDE the form for the live-updating dropdowns
col1, col2 = st.columns(2)
with col1:
    supervisor = st.selectbox("Supervisor", ["Prasanth", "RamaSai", "Sunil", "Ravindra", "Naresh", "Subodth"])
    worker = st.selectbox("Worker Name", workers)
    job_code = st.selectbox("Job Code", job_list)
with col2:
    # This selection now triggers an immediate change in unit_label
    activity = st.selectbox("Activity", list(UNITS.keys()))
    unit_label = UNITS[activity] # <--- THIS NOW UPDATES INSTANTLY
    output = st.number_input(f"Output ({unit_label})", min_value=0.0)
    hours = st.number_input("Man-Hours Spent", min_value=0.0, step=0.5)
    notes = st.text_area("Remarks/Notes")

if st.button("🚀 Submit Production Log"):
    ts = datetime.now(IST).strftime('%Y-%m-%d %H:%M')
    new_row = [ts, supervisor, worker, job_code, activity, unit_label, output, hours, notes]
    
    if os.path.exists(LOGS_FILE):
        try:
            df = pd.read_csv(LOGS_FILE)
            df = df.loc[:, ~df.columns.duplicated()]
            df = df.rename(columns={'Job': 'Job_Code', 'Remarks': 'Notes'})
            new_df = pd.DataFrame([new_row], columns=HEADERS)
            df = pd.concat([df[HEADERS], new_df], ignore_index=True)
        except:
            df = pd.DataFrame([new_row], columns=HEADERS)
    else:
        df = pd.DataFrame([new_row], columns=HEADERS)
    
    df.to_csv(LOGS_FILE, index=False)
    sync_to_github(LOGS_FILE)
    st.success(f"✅ Logged & Synced at {ts}")
    st.rerun()

# --- 4. DISPLAY (TODAY ONLY) ---
st.divider()
if os.path.exists(LOGS_FILE):
    df_view = pd.read_csv(LOGS_FILE).reindex(columns=HEADERS)
    
    # Create a Date column for temporary filtering
    df_view['Date'] = pd.to_datetime(df_view['Timestamp']).dt.date
    today_ist = datetime.now(IST).date()
    
    # Filter for the main dashboard table
    df_today = df_view[df_view['Date'] == today_ist].drop(columns=['Date'])
    df_all = df_view.sort_values(by="Timestamp", ascending=False).drop(columns=['Date'])

    st.subheader("📊 Today's Job Progress")
    if not df_today.empty:
        # Show only today's work at the top
        st.table(df_today.sort_values(by="Timestamp", ascending=False))
    else:
        st.info(f"No entries recorded yet for today ({today_ist}).")

    with st.expander("🔍 View All Historical Detailed Logs", expanded=False):
        st.dataframe(df_all, use_container_width=True)
        csv = df_all.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Full CSV Report", csv, "Full_Production_Report.csv")
# --- 5. MANAGEMENT & SUMMARY (CLEAN VIEW) ---
st.divider()
st.header("📊 Management & Production Summary")

if os.path.exists(LOGS_FILE):
    df_mngt = pd.read_csv(LOGS_FILE)
    df_mngt['Date'] = pd.to_datetime(df_mngt['Timestamp']).dt.date
    
    # --- A. ADVANCED SEARCH ---
    st.subheader("🔍 Filter Records")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # DEFAULT TO TODAY ONLY
        today = datetime.now(IST).date()
        date_pick = st.date_input("Select Date / Range", value=today)
        
        # Filtering logic for Today, Single Date, or Range
        if isinstance(date_pick, (list, tuple)) and len(date_pick) == 2:
            mask = (df_mngt['Date'] >= date_pick[0]) & (df_mngt['Date'] <= date_pick[1])
        elif isinstance(date_pick, (list, tuple)) and len(date_pick) == 1:
            mask = (df_mngt['Date'] == date_pick[0])
        else:
            mask = (df_mngt['Date'] == date_pick)

    with col2:
        search_job = st.multiselect("Filter by Job", options=sorted(df_mngt['Job_Code'].unique()))
    with col3:
        search_worker = st.multiselect("Filter by Worker", options=sorted(df_mngt['Worker'].unique()))

    # Apply Filters
    filtered_df = df_mngt[mask]
    if search_job: filtered_df = filtered_df[filtered_df['Job_Code'].isin(search_job)]
    if search_worker: filtered_df = filtered_df[filtered_df['Worker'].isin(search_worker)]
    
    # SHOW FILTERED DATA
    if not filtered_df.empty:
        st.write(f"Showing **{len(filtered_df)}** records for the selected period.")
        st.dataframe(filtered_df.sort_values(by="Timestamp", ascending=False), use_container_width=True)
        
        # --- B. SUMMARIES ---
        st.subheader("📈 Period Totals")
        choice_map = {"Job Code": "Job_Code", "Worker": "Worker", "Activity": "Activity"}
        summary_choice = st.radio("Group By:", list(choice_map.keys()), horizontal=True)
        
        summary_table = filtered_df.groupby(choice_map[summary_choice]).agg({'Output': 'sum', 'Hours': 'sum'}).reset_index()
        st.table(summary_table)
    else:
        st.info("No records found for this date. Change the date filter above to see history.")

    # --- C. EXCEL & CLEANUP (Keep these at the bottom) ---
    st.divider()
    col_ex, col_del = st.columns(2)
    with col_ex:
        def to_excel(df):
            import io
            output = io.BytesIO()
            try:
                writer = pd.ExcelWriter(output, engine='xlsxwriter')
                df.to_excel(writer, index=False, sheet_name='Production_Logs')
                writer.close()
                return output.getvalue()
            except: return None

        excel_data = to_excel(df_mngt)
        if excel_data:
            st.download_button("📥 Download Master Excel", data=excel_data, 
                               file_name=f"BG_Master_Report_{today}.xlsx")
    
    with col_del:
        with st.expander("🗑️ Delete Entry"):
            if not filtered_df.empty:
                delete_options = filtered_df['Timestamp'].astype(str) + " | " + filtered_df['Worker'] + " | " + filtered_df['Job_Code']
                to_delete = st.selectbox("Select to remove", delete_options)
                if st.button("❌ Confirm Delete"):
                    ts_del, work_del, job_del = to_delete.split(" | ")
                    df_final = df_mngt[~((df_mngt['Timestamp'].astype(str) == ts_del) & 
                                         (df_mngt['Worker'] == work_del) & 
                                         (df_mngt['Job_Code'] == job_del))]
                    df_final.drop(columns=['Date'], errors='ignore').to_csv(LOGS_FILE, index=False)
                    sync_to_github(LOGS_FILE)
                    st.rerun()

