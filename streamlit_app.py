import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import json

# Set page config
st.set_page_config(page_title="Google Search Results Parser", page_icon="🔍", layout="wide")

# Load the SerpAPI key and credentials from the secrets file
SERPAPI_KEY = st.secrets["serpapi"]["api_key"]
USERNAME = st.secrets["credentials"]["username"]
PASSWORD = st.secrets["credentials"]["password"]

def fetch_search_results(query: str, num_results: int):
    if not SERPAPI_KEY:
        st.error("SerpAPI key is missing. Please check your secrets.")
        return {}

    params = {
        "api_key": SERPAPI_KEY,
        "engine": "google",
        "q": query,
        "num": num_results,
        "location": "Austin, Texas, United States"
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        return results
    except Exception as e:
        st.error(f"Error fetching search results: {str(e)}")
        return {}

def display_results_table(results):
    for key, value in results.items():
        if isinstance(value, list) and value:
            st.subheader(f"{key.replace('_', ' ').title()}")
            df = pd.json_normalize(value)
            st.dataframe(df, use_container_width=True)
            
            for i, item in enumerate(value):
                with st.expander(f"{key.replace('_', ' ').title()} {i+1} Full JSON"):
                    st.json(item)
        elif isinstance(value, dict) and value:
            st.subheader(f"{key.replace('_', ' ').title()}")
            st.json(value)

def login():
    st.sidebar.title("Login")
    with st.sidebar.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")

        if submit_button:
            if username == USERNAME and password == PASSWORD:
                st.session_state["logged_in"] = True
                st.success("Logged in successfully!")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login()
    else:
        st.title("Google Search Results Parser")

        query = st.text_input("Enter search query:")
        num_results = st.slider("Number of results to fetch", min_value=1, max_value=100, value=10)

        if st.button("Search"):
            with st.spinner("Fetching results..."):
                results = fetch_search_results(query, num_results)
                
                if results:
                    display_results_table(results)
                    
                    # Display raw results
                    with st.expander("Raw JSON Results"):
                        st.json(results)
                else:
                    st.error("No results to display. Please try a different query.")

        if st.sidebar.button("Logout"):
            st.session_state["logged_in"] = False
            st.experimental_rerun()

if __name__ == "__main__":
    main()
