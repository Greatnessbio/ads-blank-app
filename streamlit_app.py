import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import json
import base64

# Set page config
st.set_page_config(page_title="Google Search Results Analyzer", page_icon="🔍", layout="wide")

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
    tables = {}
    for key, value in results.items():
        if isinstance(value, list) and value:
            df = pd.json_normalize(value)
            tables[key] = df
    
    return tables

def get_download_link(data, filename, text):
    csv = data.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

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
        st.title("Google Search Results Analyzer")
        query = st.text_input("Enter search query:")
        num_results = st.slider("Number of results to fetch", min_value=1, max_value=100, value=10)
        
        if st.button("Search"):
            with st.spinner("Fetching results..."):
                results = fetch_search_results(query, num_results)
                
                if results:
                    st.session_state["search_results"] = results
                    tables = display_results_table(results)
                    
                    # Display tables
                    for key, df in tables.items():
                        st.subheader(f"{key.replace('_', ' ').title()}")
                        st.dataframe(df, use_container_width=True)
                    
                    # Prepare download links
                    download_links = []
                    for key, df in tables.items():
                        filename = f"{key}_results.csv"
                        link = get_download_link(df, filename, f"Download {key.replace('_', ' ').title()} CSV")
                        download_links.append(link)
                    
                    # Add download buttons and raw JSON under a single dropdown
                    with st.expander("Download Options and Raw Data"):
                        st.subheader("Download CSV Files")
                        for link in download_links:
                            st.markdown(link, unsafe_allow_html=True)
                        
                        st.subheader("Raw JSON Data")
                        st.json(results)
                    
                    # Analysis section
                    st.subheader("Quick Analysis PLACEHOLDER FOR AI")
                    if 'ads' in tables:
                        st.write(f"Number of ads: {len(tables['ads'])}")
                    if 'organic_results' in tables:
                        st.write(f"Number of organic results: {len(tables['organic_results'])}")
                    
                    # TODO: Add more in-depth analysis here
                    st.write("For beating ads and improving search rankings, consider:")
                    st.write("1. Analyzing ad copy and keywords used in top ads")
                    st.write("2. Identifying common themes in organic results")
                    st.write("3. Checking the 'people also ask' section for content ideas")
                    st.write("4. Examining related searches for additional keyword opportunities")
                else:
                    st.error("No results to display. Please try a different query.")
        
        if st.sidebar.button("Logout"):
            st.session_state["logged_in"] = False
            st.experimental_rerun()

if __name__ == "__main__":
    main()
