import pandas as pd
import os
import streamlit as st

@st.cache_data
def load_data():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(BASE_DIR, "data", "StudentsPerformance.csv")
    return pd.read_csv(data_path)
