import streamlit as st
import requests
import pandas as pd
import json
import re
from streamlit.logger import get_logger

LOGGER = get_logger(__name__)

# Set page config at the very beginning
st.set_page_config(page_title="Google Search Results Parser", page_icon="🔍", layout="wide")

# Load the SerpAPI key and credentials from the secrets file
SERPAPI_KEY = st.secrets["serpapi"]["api_key"]
USERNAME = st.secrets["credentials"]["username"]
PASSWORD = st.secrets["credentials"]["password"]

def load_api_key():
    try:
        return st.secrets["secrets"]["openrouter_api_key"]
    except KeyError:
        st.error("OpenRouter API key not found in secrets.toml. Please add it.")
        return None

@st.cache_data(ttl=300)
def fetch_google_search_results(query: str):
    if not SERPAPI_KEY:
        st.error("SerpAPI key is missing. Please check your secrets.")
        return {}
    
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "location": "Austin, Texas, United States",
        "hl": "en",
        "gl": "us"
    }
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        results = response.json()
        return results
    except requests.RequestException as e:
        st.error(f"Error fetching search results: {str(e)}")
        return {}

def parse_results(results):
    ads = results.get('ads', [])
    organic_results = results.get('organic_results', [])
    
    parsed_data = {
        'ads': [],
        'organic': []
    }
    
    for ad in ads[:10]:
        parsed_data['ads'].append({
            'Type': 'Ad',
            'Position': ad.get('position'),
            'Title': ad.get('title'),
            'Link': ad.get('link'),
            'Displayed Link': ad.get('displayed_link'),
            'Description': ad.get('description'),
        })
    
    for result in organic_results[:10]:
        parsed_data['organic'].append({
            'Type': 'Organic',
            'Title': result.get('title'),
            'Link': result.get('link'),
            'Snippet': result.get('snippet')
        })
    
    return parsed_data

def display_results_table(parsed_data):
    st.subheader("Ad Results")
    if parsed_data['ads']:
        df_ads = pd.DataFrame(parsed_data['ads'])
        st.dataframe(df_ads, use_container_width=True)
    else:
        st.info("No ad results found.")
    
    st.subheader("Organic Results")
    if parsed_data['organic']:
        df_organic = pd.DataFrame(parsed_data['organic'])
        st.dataframe(df_organic, use_container_width=True)
    else:
        st.info("No organic results found.")

def analyze_row(row):
    api_key = load_api_key()
    if not api_key:
        return "API key not found."

    prompt = f"Analyze this search result data and provide insights for digital marketing:\n\n{row.to_json()}"
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [
                    {"role": "system", "content": "You are a digital marketing analyst."},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.RequestException as e:
        LOGGER.error(f"API request failed: {e}")
        return "Failed to analyze row."
    except (KeyError, IndexError, ValueError) as e:
        LOGGER.error(f"Error processing API response: {e}")
        return "Error processing the analysis."

def process_results(results):
    df_ads = pd.DataFrame(results['ads'])
    df_organic = pd.DataFrame(results['organic'])
    
    if 'analyzed_results' not in st.session_state:
        st.session_state.analyzed_results = {}
    
    for index, row in df_ads.iterrows():
        if index not in st.session_state.analyzed_results:
            analysis = analyze_row(row)
            st.session_state.analyzed_results[index] = analysis
        
        st.write(f"Ad Result {index + 1}:")
        st.write(row)
        st.write("Analysis:")
        st.write(st.session_state.analyzed_results[index])
        st.write("---")
    
    for index, row in df_organic.iterrows():
        if index + len(df_ads) not in st.session_state.analyzed_results:
            analysis = analyze_row(row)
            st.session_state.analyzed_results[index + len(df_ads)] = analysis
        
        st.write(f"Organic Result {index + 1}:")
        st.write(row)
        st.write("Analysis:")
        st.write(st.session_state.analyzed_results[index + len(df_ads)])
        st.write("---")

def login():
    st.title("Login")
    with st.form("login_form"):
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
        
        query = st.text_input("Enter search query:", "elisa kits il-6")
        search_button = st.button("Search")
        
        if search_button:
            with st.spinner("Fetching results..."):
                results = fetch_google_search_results(query)
                parsed_data = parse_results(results)
                
                st.subheader("Search Information")
                st.write(f"Total results: {results.get('search_information', {}).get('total_results', 'N/A')}")
                st.write(f"Time taken: {results.get('search_information', {}).get('time_taken_displayed', 'N/A')} seconds")
                
                display_results_table(parsed_data)
                
                st.subheader("Raw JSON Results")
                st.json(results)
                
                process_results(parsed_data)

        if st.button("Show Stored Analyses"):
            for index, analysis in st.session_state.analyzed_results.items():
                st.write(f"Analysis for Result {index + 1}:")
                st.write(analysis)
                st.write("---")

if __name__ == "__main__":
    main()
