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

def fetch_search_results(query: str, num_results: int, location: str, language: str, country: str):
    if not SERPAPI_KEY:
        st.error("SerpAPI key is missing. Please check your secrets.")
        return {}
    params = {
        "api_key": SERPAPI_KEY,
        "engine": "google",
        "q": query,
        "num": num_results,
        "location": location,
        "hl": language,
        "gl": country
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

def get_country_name(country_code):
    country_names = {
        "us": "the United States",
        "uk": "the United Kingdom",
        "ca": "Canada",
        "au": "Australia",
        "in": "India"
    }
    return country_names.get(country_code, country_code)

def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if not st.session_state["logged_in"]:
        login()
    else:
        st.title("Google Search Results Analyzer")
        
        # Search parameters
        col1, col2 = st.columns(2)
        with col1:
            query = st.text_input("Enter search query:")
            num_results = st.slider("Number of results to fetch", min_value=1, max_value=100, value=10)
            location = st.text_input("Location (e.g., New York, NY)", value="Austin, Texas, United States")
        with col2:
            language = st.selectbox("Language", options=["en", "es", "fr", "de", "it"], format_func=lambda x: {"en": "English", "es": "Spanish", "fr": "French", "de": "German", "it": "Italian"}[x])
            country = st.selectbox("Country", options=["us", "uk", "ca", "au", "in"], format_func=lambda x: {"us": "United States", "uk": "United Kingdom", "ca": "Canada", "au": "Australia", "in": "India"}[x])
        
        if st.button("Search"):
            with st.spinner("Fetching results..."):
                results = fetch_search_results(query, num_results, location, language, country)
                
                if results:
                    st.session_state["search_results"] = results
                    
                    display_results_table(results)
                    
                    # Display raw results
                    with st.expander("Raw JSON Results"):
                        st.json(results)
                    
                    # Quick Analysis
                    st.subheader("Quick Analysis")
                    if 'ads' in results:
                        st.write(f"Number of ads: {len(results['ads'])}")
                    if 'organic_results' in results:
                        st.write(f"Number of organic results: {len(results['organic_results'])}")
                    
                    st.write("For beating ads and improving search rankings, consider:")
                    st.write("1. Analyzing ad copy and keywords used in top ads")
                    st.write("2. Identifying common themes in organic results")
                    st.write("3. Checking the 'people also ask' section for content ideas")
                    st.write("4. Examining related searches for additional keyword opportunities")
                    st.write(f"5. Analyzing results specific to {location} and {get_country_name(country)}")
                    
                    # Additional ad analysis
                    if 'ads' in results:
                        st.subheader("Ad Analysis")
                        ad_positions = [ad.get('position', 'N/A') for ad in results['ads']]
                        st.write(f"Ad positions: {ad_positions}")
                        ad_titles = [ad.get('title', 'N/A') for ad in results['ads']]
                        st.write("Common words in ad titles:")
                        st.write(pd.Series(' '.join(ad_titles).lower().split()).value_counts().head())
                else:
                    st.error("No results to display. Please try a different query.")
        
        if st.sidebar.button("Logout"):
            st.session_state["logged_in"] = False
            st.experimental_rerun()

if __name__ == "__main__":
    main()
