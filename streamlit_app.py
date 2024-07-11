import streamlit as st
import requests
import pandas as pd
import json
from streamlit.logger import get_logger
import base64

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
def fetch_google_search_results(query: str, num_results: int):
    if not SERPAPI_KEY:
        st.error("SerpAPI key is missing. Please check your secrets.")
        return {}
    
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num_results,
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

def parse_results(results, num_results):
    ads = results.get('ads', [])
    organic_results = results.get('organic_results', [])
    
    parsed_data = {
        'ads': [],
        'organic': []
    }
    
    for ad in ads[:num_results]:
        parsed_data['ads'].append({
            'Type': 'Ad',
            'Position': ad.get('position'),
            'Title': ad.get('title'),
            'Link': ad.get('link'),
            'Displayed Link': ad.get('displayed_link'),
            'Description': ad.get('description'),
        })
    
    for result in organic_results[:num_results]:
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

    prompt = f"""Analyze this search result data and provide insights for digital marketing:

{row.to_json()}

Please provide a comprehensive analysis including:
1. SEO strengths and weaknesses (for organic results) or Ad copy effectiveness (for ads)
2. Content strategy insights
3. Keyword optimization suggestions
4. Competitive positioning
5. Potential areas for improvement
6. Unique selling propositions (if applicable)
7. Call-to-action effectiveness
8. Target audience insights
9. Recommendations for outranking this result (for organic) or creating more effective ads (for ads)

Be specific and provide actionable insights a digital marketer can use to compete with or outrank this result."""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [
                    {"role": "system", "content": "You are an expert digital marketing analyst specializing in SEO, PPC, and competitive analysis."},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.RequestException as e:
        LOGGER.error(f"API request failed: {e}")
        return "Failed to analyze row."
    except (KeyError, IndexError, ValueError) as e:
        LOGGER.error(f"Error processing API response: {e}")
        return "Error processing the analysis."

def process_results(results, result_type):
    df = pd.DataFrame(results[result_type])
    
    if 'analyzed_results' not in st.session_state:
        st.session_state.analyzed_results = {}
    
    for index, row in df.iterrows():
        key = f"{result_type}_{index}"
        if key not in st.session_state.analyzed_results:
            analysis = analyze_row(row)
            st.session_state.analyzed_results[key] = analysis
        
        st.write(f"{result_type.capitalize()} Result {index + 1}:")
        st.write(row)
        st.write("Analysis:")
        st.write(st.session_state.analyzed_results[key])
        st.write("---")

def generate_report(query, parsed_data):
    report = f"# Search Results Analysis for '{query}'\n\n"
    
    for result_type in ['ads', 'organic']:
        if parsed_data[result_type]:
            report += f"## {result_type.capitalize()} Results\n\n"
            for index, result in enumerate(parsed_data[result_type]):
                report += f"### {result_type.capitalize()} Result {index + 1}\n\n"
                for key, value in result.items():
                    report += f"**{key}:** {value}\n\n"
                key = f"{result_type}_{index}"
                if key in st.session_state.analyzed_results:
                    report += f"#### Analysis:\n\n{st.session_state.analyzed_results[key]}\n\n"
                report += "---\n\n"
    
    return report

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
        num_results = st.slider("Number of results to fetch", min_value=1, max_value=10, value=5)
        
        search_button = st.button("Search")
        
        if search_button or 'parsed_data' in st.session_state:
            if search_button:
                with st.spinner("Fetching results..."):
                    results = fetch_google_search_results(query, num_results)
                    parsed_data = parse_results(results, num_results)
                    st.session_state.parsed_data = parsed_data
                    st.session_state.raw_results = results
            else:
                parsed_data = st.session_state.parsed_data
                results = st.session_state.raw_results
            
            st.subheader("Search Information")
            st.write(f"Total results: {results.get('search_information', {}).get('total_results', 'N/A')}")
            st.write(f"Time taken: {results.get('search_information', {}).get('time_taken_displayed', 'N/A')} seconds")
            
            display_results_table(parsed_data)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Analyze Ads"):
                    process_results(parsed_data, 'ads')
            with col2:
                if st.button("Analyze Organic"):
                    process_results(parsed_data, 'organic')
            
            # Generate and provide download link for the report
            report = generate_report(query, parsed_data)
            report_bytes = report.encode('utf-8')
            st.download_button(
                label="Download Full Report",
                data=report_bytes,
                file_name="search_results_analysis.md",
                mime="text/markdown"
            )
            
            st.subheader("Raw JSON Results")
            st.json(results)

        if st.button("Show Stored Analyses"):
            for key, analysis in st.session_state.analyzed_results.items():
                result_type, index = key.split("_")
                st.write(f"Analysis for {result_type.capitalize()} Result {int(index) + 1}:")
                st.write(analysis)
                st.write("---")

if __name__ == "__main__":
    main()
