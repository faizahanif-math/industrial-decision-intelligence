import psycopg
import streamlit as st

def get_connection():
    params = {
        "host": st.secrets["postgres"]["host"],
        "port": st.secrets["postgres"]["port"],
        "dbname": st.secrets["postgres"]["dbname"],
        "user": st.secrets["postgres"]["user"],
        "password": st.secrets["postgres"]["password"],
    }
    # Optional SSL mode (needed for Neon cloud database)
    if "sslmode" in st.secrets["postgres"]:
        params["sslmode"] = st.secrets["postgres"]["sslmode"]
    return psycopg.connect(**params)