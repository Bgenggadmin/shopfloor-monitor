import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. Establish Backend Connection
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🏗️ B&G Engineering Industries")
st.subheader("Shopfloor Production Log")

# 2. Daily Entry Form
with st.form("production_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        supervisor = st.selectbox("Logged By (Supervisor)", ["Prasanth", "RamaSai", "Subodth"])
        unit = st.selectbox("Unit", ["A", "B", "C"])
        worker = st.selectbox("Worker", ["Suresh", "Naresh", "Ravindra"])
        job_code = st.selectbox("Job Code", ["JOB-101", "SSR501", "SSR502"])
    
    with col2:
        category = st.selectbox("Category", ["Welder", "Fitter", "Helper"])
        activity = st.selectbox("Activity", ["Meters Weld", "Fitup", "Grinding"])
        hours = st.number_input("Man-Hours Spent", min_value=0.0, step=0.5)
        output = st.number_input("Output Value (Meters/Qty)", min_value=0.0, step=0.1)

    remarks = st.text_input("Remarks")
    
    submit = st.form_submit_button("Submit to Backend")

    if submit:
        try:
            # Prepare data row
            new_row = pd.DataFrame([{
                "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "Supervisor": supervisor,
                "Unit": unit,
                "Worker": worker,
                "Job_Code": job_code,
                "Category": category,
                "Activity": activity,
                "Hours": hours,
                "Output": output,
                "Remarks": remarks
            }])

            # Read current data from the Production_Logs tab
            existing_df = conn.read(worksheet="Production_Logs")
            
            # Combine and Update
            updated_df = pd.concat([existing_df, new_row], ignore_index=True)
            conn.update(worksheet="Production_Logs", data=updated_df)
            
            st.balloons()
            st.success("✅ Log successfully saved to Google Sheets backend!")
        except Exception as e:
            st.error(f"❌ Backend Error: {e}")
            st.info("Check if the Sheet is shared with the bg-logger email as Editor.")

# 3. Simple View for Local Saving
if st.checkbox("View Backend Records"):
    try:
        df = conn.read(worksheet="Production_Logs", ttl="0")
        st.dataframe(df.sort_values(by="Timestamp", ascending=False))
        
        # Simple Download button to save to your local system before code changes
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Records to Excel/CSV", data=csv, file_name="bg_production_logs.csv", mime="text/csv")
    except:
        st.write("No records in backend yet.")
