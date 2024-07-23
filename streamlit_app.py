import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import json
import base64

# Set page config
st.set_page_config(page_title="Google Search Results Parser", page_icon="🔍", layout="wide")

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
        "gl": country,
        "google_domain": "google.com"
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
        st.title("Google Search Results Parser")
        
        # Search parameters
        col1, col2 = st.columns(2)
        with col1:
            query = st.text_input("Enter search query:", value="hot dogs")
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
                    st.subheader("Quick Analysis")
                    
                    # Check for ads
                    if 'ads' in results:
                        st.write(f"Number of ads: {len(results['ads'])}")
                        st.subheader("Ad Details")
                        for i, ad in enumerate(results['ads'], 1):
                            st.write(f"Ad {i}:")
                            st.write(f"Title: {ad.get('title', 'N/A')}")
                            st.write(f"Link: {ad.get('link', 'N/A')}")
                            st.write(f"Description: {ad.get('description', 'N/A')}")
                            st.write(f"Position: {ad.get('position', 'N/A')}")
                            st.write(f"Block Position: {ad.get('block_position', 'N/A')}")
                            if 'sitelinks' in ad:
                                st.write("Sitelinks:")
                                for sitelink in ad['sitelinks']:
                                    st.write(f"- {sitelink.get('title', 'N/A')}: {sitelink.get('link', 'N/A')}")
                            st.write("---")
                    else:
                        st.info("No ads were found for this search query.")

                    # Check for shopping results
                    if 'shopping_results' in results:
                        st.write(f"Number of shopping results: {len(results['shopping_results'])}")
                        st.subheader("Shopping Results")
                        for i, item in enumerate(results['shopping_results'], 1):
                            st.write(f"Item {i}:")
                            st.write(f"Title: {item.get('title', 'N/A')}")
                            st.write(f"Price: {item.get('price', 'N/A')}")
                            st.write(f"Link: {item.get('link', 'N/A')}")
                            st.write("---")
                    else:
                        st.info("No shopping results were found for this search query.")
                    
                    if 'organic_results' in tables:
                        st.write(f"Number of organic results: {len(tables['organic_results'])}")
                    
                    st.write("For beating ads and improving search rankings, consider:")
                    st.write("1. Analyzing ad copy and keywords used in top ads (when present)")
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
