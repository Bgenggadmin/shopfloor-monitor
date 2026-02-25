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

# --- 4. DISPLAY ---
st.divider()
if os.path.exists(LOGS_FILE):
    df_view = pd.read_csv(LOGS_FILE).reindex(columns=HEADERS)
    df_display = df_view.sort_values(by="Timestamp", ascending=False)
    st.subheader("📊 Job Progress Summary")
    st.table(df_display.head(10)) 
    with st.expander("🔍 View All Detailed Logs", expanded=True):
        st.dataframe(df_display, use_container_width=True)
        csv = df_view.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel Report", csv, "BG_Production_Report.csv")
# --- 5. MANAGEMENT, SUMMARY & EXCEL REPORTS ---
st.divider()
st.header("📊 Management & Production Summary")

if os.path.exists(LOGS_FILE):
    df_mngt = pd.read_csv(LOGS_FILE)
    df_mngt['Date'] = pd.to_datetime(df_mngt['Timestamp']).dt.date
    
    # --- A. EXCEL DOWNLOAD (TOP) ---
    # Convert whole log to Excel for office records
    def to_excel(df):
        import io
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Production_Logs')
        writer.close()
        return output.getvalue()

    st.download_button(
        label="📥 Download Full Excel Report",
        data=to_excel(df_mngt),
        file_name=f"BG_Production_Report_{datetime.now(IST).strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.ms-excel"
    )

    # --- B. ADVANCED SEARCH ---
    st.subheader("🔍 Advanced Search")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        # STABLE DATE SELECTOR: Prevents StreamlitAPIException
        min_d, max_d = df_mngt['Date'].min(), df_mngt['Date'].max()
        try:
            date_range = st.date_input("Filter by Date Range", value=(min_d, max_d))
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                mask = (df_mngt['Date'] >= date_range[0]) & (df_mngt['Date'] <= date_range[1])
            else:
                mask = (df_mngt['Date'] == (date_range[0] if isinstance(date_range, (list, tuple)) else date_range))
        except:
            mask = df_mngt['Date'].notna() # Fallback to show all if picker is in transition

    with col_f2:
        search_job = st.multiselect("Filter by Job", options=sorted(df_mngt['Job_Code'].unique()))
    with col_f3:
        search_worker = st.multiselect("Filter by Worker", options=sorted(df_mngt['Worker'].unique()))

    # Apply Filters
    filtered_df = df_mngt[mask]
    if search_job:
        filtered_df = filtered_df[filtered_df['Job_Code'].isin(search_job)]
    if search_worker:
        filtered_df = filtered_df[filtered_df['Worker'].isin(search_worker)]

    st.dataframe(filtered_df.sort_values(by="Timestamp", ascending=False), use_container_width=True)

    # --- C. SUMMARIES ---
    st.subheader("📈 Production Totals")
    choice_map = {"Job Code": "Job_Code", "Worker": "Worker", "Activity": "Activity"}
    summary_choice = st.radio("Sum up totals by:", list(choice_map.keys()), horizontal=True)
    actual_col = choice_map[summary_choice]
    
    if not filtered_df.empty:
        summary_table = filtered_df.groupby(actual_col).agg({'Output': 'sum', 'Hours': 'sum'}).reset_index()
        st.table(summary_table)

    # --- D. DELETE ENTRY ---
    st.subheader("🗑️ Data Cleanup")
    with st.expander("Delete an accidental entry"):
        delete_options = filtered_df['Timestamp'] + " | " + filtered_df['Worker'] + " | " + filtered_df['Job_Code']
        to_delete = st.selectbox("Select record to remove", delete_options)
        if st.button("❌ Permanent Delete"):
            ts_del, work_del, job_del = to_delete.split(" | ")
            df_final = df_mngt[~((df_mngt['Timestamp'] == ts_del) & 
                                 (df_mngt['Worker'] == work_del) & 
                                 (df_mngt['Job_Code'] == job_del))]
            df_final.drop(columns=['Date'], errors='ignore').to_csv(LOGS_FILE, index=False)
            sync_to_github(LOGS_FILE)
            st.success("Entry deleted. Refreshing...")
            st.rerun()
else:
    st.info("No production logs found yet.")
