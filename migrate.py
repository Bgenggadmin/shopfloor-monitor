import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os

st.title("📂 One-Time Data Migrator")

# 1. Connect to Supabase
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("Secrets missing! Add URL and KEY to Streamlit.")
    st.stop()

# 2. Find your CSV
csv_path = "production_logs.csv"

if not os.path.exists(csv_path):
    st.error(f"Cannot find {csv_path} in your main GitHub folder.")
else:
    df = pd.read_csv(csv_path)
    st.write("Preview of data to be moved:", df.head())

    if st.button("🚀 Start Migration"):
        # We convert the CSV rows into a format the database understands
        records = df.to_dict(orient='records')
        
        try:
            # This sends all rows to the 'production' table at once
            supabase.table("production").insert(records).execute()
            st.success(f"✅ Success! {len(records)} rows moved to the cloud.")
            st.info("You can now go back to your main app. Delete this file after checking!")
        except Exception as e:
            st.error(f"Migration failed: {e}")
