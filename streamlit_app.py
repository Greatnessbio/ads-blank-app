import streamlit as st
import requests
import pandas as pd
import json
from streamlit.logger import get_logger
import base64
from serpapi import GoogleSearch

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
        "gl": "us",
        "include_ads": "true"  # Explicitly request ad results
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Log the full response for debugging
        LOGGER.info(f"Full API response: {json.dumps(results, indent=2)}")
        
        return results
    except Exception as e:
        st.error(f"Error fetching search results: {str(e)}")
        return {}

def parse_results(results, num_results):
    parsed_data = {
        'ads': [],
        'organic': []
    }
    
    # Check for ads in multiple possible locations
    ad_sources = ['ads', 'shopping_results', 'paid_products', 'immersive_products']
    for source in ad_sources:
        if source in results:
            for item in results[source][:num_results]:
                parsed_data['ads'].append({
                    'Type': 'Ad',
                    'Position': item.get('position'),
                    'Title': item.get('title'),
                    'Link': item.get('link'),
                    'Displayed Link': item.get('displayed_link'),
                    'Price': item.get('price'),
                    'Source': item.get('source'),
                    'Rating': item.get('rating'),
                    'Reviews': item.get('reviews'),
                })
    
    # Parse organic results
    if 'organic_results' in results:
        for result in results['organic_results'][:num_results]:
            parsed_data['organic'].append({
                'Type': 'Organic',
                'Title': result.get('title'),
                'Link': result.get('link'),
                'Snippet': result.get('snippet')
            })
    
    return parsed_data

def display_results_table(parsed_data):
    for result_type in ['ads', 'organic']:
        st.subheader(f"{result_type.capitalize()} Results")
        if parsed_data[result_type]:
            df = pd.DataFrame(parsed_data[result_type])
            st.dataframe(df, use_container_width=True)
        else:
            st.info(f"No {result_type} results found.")

@st.cache_data(ttl=3600)
def analyze_row(_row, api_key):
    prompt = f"""Analyze this search result data and provide insights for digital marketing:

{_row.to_json()}

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
    api_key = load_api_key()
    if not api_key:
        st.error("API key not found.")
        return
    
    df = pd.DataFrame(results[result_type])
    
    if 'analyzed_results' not in st.session_state:
        st.session_state.analyzed_results = {}
    
    for index, row in df.iterrows():
        key = f"{result_type}_{index}"
        if key not in st.session_state.analyzed_results:
            with st.spinner(f"Analyzing {result_type.capitalize()} Result {index + 1}..."):
                analysis = analyze_row(row, api_key)
                st.session_state.analyzed_results[key] = analysis
        
        with st.expander(f"{result_type.capitalize()} Result {index + 1}"):
            st.write(row)
            st.write("Analysis:")
            st.write(st.session_state.analyzed_results[key])

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

def get_download_link(content, filename, text):
    b64 = base64.b64encode(content.encode()).decode()
    return f'<a href="data:file/txt;base64,{b64}" download="{filename}">{text}</a>'

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
        
        query = st.text_input("Enter search query:", "hot dogs")
        num_results = st.slider("Number of results to fetch", min_value=1, max_value=10, value=5)
        
        search_button = st.button("Search")
        
        if search_button or 'parsed_data' in st.session_state:
            if search_button:
                with st.spinner("Fetching results..."):
                    results = fetch_google_search_results(query, num_results)
                    parsed_data = parse_results(results, num_results)
                    st.session_state.parsed_data = parsed_data
                    st.session_state.raw_results = results
                    st.session_state.analyzed_results = {}  # Clear previous analyses
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
            
            if st.session_state.analyzed_results:
                st.subheader("Analysis Results")
                for result_type in ['ads', 'organic']:
                    if any(key.startswith(result_type) for key in st.session_state.analyzed_results):
                        st.write(f"### {result_type.capitalize()} Analyses")
                        for key, analysis in st.session_state.analyzed_results.items():
                            if key.startswith(result_type):
                                _, index = key.split("_")
                                with st.expander(f"{result_type.capitalize()} Result {int(index) + 1}"):
                                    st.write(analysis)
            
            # Generate and provide download link for the report
            report = generate_report(query, parsed_data)
            report_bytes = report.encode('utf-8')
            st.download_button(
                label="Download Full Report (Markdown)",
                data=report_bytes,
                file_name="search_results_analysis.md",
                mime="text/markdown"
            )
            
            # Raw JSON Results in a collapsible section with download option
            with st.expander("Raw JSON Results"):
                st.json(results)
                st.markdown(get_download_link(json.dumps(results, indent=2), 
                                              "raw_results.json", 
                                              "Download Raw JSON"),
                            unsafe_allow_html=True)

if __name__ == "__main__":
    main()
