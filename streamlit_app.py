import streamlit as st
import requests
import pandas as pd
import json
from streamlit.logger import get_logger
import base64
from serpapi import GoogleSearch
from typing import List, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

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
def fetch_google_search_results(query: str, num_results: int) -> Dict[str, Any]:
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
        "include_ads": "true"
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        if not results:
            st.warning("No results returned from the API. Please try a different query.")
            logger.warning(f"No results returned for query: {query}")
        logger.info(f"Full API response: {json.dumps(results, indent=2)}")
        return results
    except Exception as e:
        st.error(f"Error fetching search results: {str(e)}")
        logger.error(f"API error: {str(e)}", exc_info=True)
        return {}

def parse_results(results: Dict[str, Any], num_results: int) -> Dict[str, List[Dict[str, Any]]]:
    parsed_data = {
        'ads': [],
        'organic': [],
        'shopping_results': [],
        'immersive_products': []
    }

    def parse_item(item: Dict[str, Any], item_type: str) -> Dict[str, Any]:
        default_data = {
            'Type': item_type,
            'Position': 'N/A',
            'Title': 'N/A',
            'Link': 'N/A',
            'Displayed Link': 'N/A',
            'Description': 'N/A',
            'Sitelinks': 'N/A',
            'Source': 'N/A'
        }
        parsed_item = default_data.copy()
        
        for key, value in item.items():
            if key in parsed_item:
                parsed_item[key] = value
        
        if item_type == 'Ad':
            parsed_item['Sitelinks'] = ', '.join([sitelink.get('title', '') for sitelink in item.get('sitelinks', [])])
        elif item_type == 'Organic':
            parsed_item['Sitelinks'] = ', '.join([sitelink.get('title', '') for sitelink in item.get('sitelinks', {}).get('inline', [])])
            parsed_item['Description'] = item.get('snippet', 'N/A')
        elif item_type in ['Shopping', 'Immersive Product']:
            parsed_item['Price'] = item.get('price', 'N/A')
            parsed_item['Rating'] = item.get('rating', 'N/A')
            parsed_item['Reviews'] = item.get('reviews', 'N/A')
        
        return parsed_item

    for key, item_type in [('ads', 'Ad'), ('organic_results', 'Organic'), ('shopping_results', 'Shopping'), ('immersive_products', 'Immersive Product')]:
        items = results.get(key, [])
        if not items:
            logger.warning(f"No {item_type} results found in API response")
        parsed_data[key.rstrip('_results')] = [parse_item(item, item_type) for item in items[:num_results]]

    return parsed_data

def analyze_row(_row: Dict[str, Any], api_key: str, query: str) -> Dict[str, Any]:
    prompt = f"""Analyze this search result data for the query '{query}' and provide insights for digital marketing:

Result Type: {_row['Type']}
Title: {_row['Title']}
Link: {_row['Link']}
Position: {_row['Position']}
Full Data: {json.dumps(_row, indent=2)}

Please provide a comprehensive analysis including:
1. SEO strengths and weaknesses (for organic results) or Ad copy effectiveness (for ads)
2. Content strategy insights
3. Keyword optimization suggestions (list top 5 keywords)
4. Competitive positioning
5. Potential areas for improvement
6. Unique selling propositions (if applicable)
7. Call-to-action effectiveness
8. Target audience insights
9. Recommendations for outranking this result (for organic) or creating more effective ads (for ads)

Be specific and provide actionable insights a digital marketer can use to compete with or outrank this result.
Format your response as a JSON object with the following keys: seo_analysis, content_strategy, keywords (as a list), competitive_positioning, improvements, usp, cta_effectiveness, target_audience, recommendations."""

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
        analysis = response.json()['choices'][0]['message']['content']
        return json.loads(analysis)
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {"error": f"Failed to analyze row: {str(e)}"}
    except (KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
        logger.error(f"Error processing API response: {e}")
        return {"error": f"Error processing the analysis: {str(e)}"}

def process_results(parsed_data: Dict[str, List[Dict[str, Any]]], query: str):
    api_key = load_api_key()
    if not api_key:
        st.error("API key not found.")
        return
    
    all_results = []
    
    for result_type, data in parsed_data.items():
        if not data:
            logger.warning(f"No results found for {result_type}")
        for index, row in enumerate(data):
            with st.spinner(f"Analyzing {result_type.capitalize().replace('_', ' ')} Result {index + 1}..."):
                analysis = analyze_row(row, api_key, query)
                result = {
                    "Type": result_type,
                    "Position": row.get('Position', 'N/A'),
                    "Title": row.get('Title', 'N/A'),
                    "Link": row.get('Link', 'N/A'),
                    "SEO Analysis": analysis.get('seo_analysis', 'N/A'),
                    "Content Strategy": analysis.get('content_strategy', 'N/A'),
                    "Keywords": ', '.join(analysis.get('keywords', ['N/A'])),
                    "Competitive Positioning": analysis.get('competitive_positioning', 'N/A'),
                    "Improvements": analysis.get('improvements', 'N/A'),
                    "USP": analysis.get('usp', 'N/A'),
                    "CTA Effectiveness": analysis.get('cta_effectiveness', 'N/A'),
                    "Target Audience": analysis.get('target_audience', 'N/A'),
                    "Recommendations": analysis.get('recommendations', 'N/A')
                }
                all_results.append(result)
    
    # Store results in session state
    st.session_state.analyzed_results = all_results

def display_results():
    if 'analyzed_results' not in st.session_state or not st.session_state.analyzed_results:
        st.warning("No analysis results available. Please run the analysis first.")
        return

    df = pd.DataFrame(st.session_state.analyzed_results)
    
    # Display interactive table
    st.subheader("Analysis Results")
    st.dataframe(df, use_container_width=True)
    
    # Download options
    if not df.empty:
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Analysis as CSV",
            data=csv,
            file_name="search_results_analysis.csv",
            mime="text/csv",
            key="download_csv"
        )
    else:
        st.info("No data available for download.")

def generate_report(query: str, analyzed_results: List[Dict[str, Any]]) -> str:
    report = f"# Search Results Analysis for '{query}'\n\n"
    
    for result in analyzed_results:
        report += f"## {result['Type']} Result - Position {result['Position']}\n\n"
        report += f"**Title:** {result['Title']}\n"
        report += f"**Link:** {result['Link']}\n\n"
        
        report += f"### SEO Analysis\n{result['SEO Analysis']}\n\n"
        report += f"### Content Strategy\n{result['Content Strategy']}\n\n"
        report += f"### Keywords\n{result['Keywords']}\n\n"
        report += f"### Competitive Positioning\n{result['Competitive Positioning']}\n\n"
        report += f"### Improvements\n{result['Improvements']}\n\n"
        report += f"### Unique Selling Proposition\n{result['USP']}\n\n"
        report += f"### Call-to-Action Effectiveness\n{result['CTA Effectiveness']}\n\n"
        report += f"### Target Audience\n{result['Target Audience']}\n\n"
        report += f"### Recommendations\n{result['Recommendations']}\n\n"
        report += "---\n\n"
    
    return report

def get_download_link(content: str, filename: str, text: str) -> str:
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
        
        query = st.text_input("Enter search query:", "biotech marketing")
        num_results = st.slider("Number of results to fetch", min_value=1, max_value=10, value=5)
        
        search_button = st.button("Search")
        
        if search_button or 'parsed_data' in st.session_state:
            if search_button:
                with st.spinner("Fetching results..."):
                    results = fetch_google_search_results(query, num_results)
                    parsed_data = parse_results(results, num_results)
                    st.session_state.parsed_data = parsed_data
                    st.session_state.raw_results = results
                    if 'analyzed_results' in st.session_state:
                        del st.session_state.analyzed_results  # Clear previous analyses
            else:
                parsed_data = st.session_state.parsed_data
                results = st.session_state.raw_results
            
            st.subheader("Search Information")
            st.write(f"Total results: {results.get('search_information', {}).get('total_results', 'N/A')}")
            st.write(f"Time taken: {results.get('search_information', {}).get('time_taken_displayed', 'N/A')} seconds")
            
            display_results_table(parsed_data)
            
            if st.button("Analyze Results", key="analyze_button"):
                process_results(parsed_data, query)
            
            display_results()
            
            # Generate and provide download link for the report
            if 'analyzed_results' in st.session_state and st.session_state.analyzed_results:
                report = generate_report(query, st.session_state.analyzed_results)
                report_bytes = report.encode('utf-8')
                st.download_button(
                    label="Download Full Report (Markdown)",
                    data=report_bytes,
                    file_name="search_results_analysis.md",
                    mime="text/markdown",
                    key="download_report"
                )
            
            # Raw JSON Results in a collapsible section with download option
            with st.expander("Raw JSON Results"):
                st.json(results)
                st.markdown(get_download_link(json.dumps(results, indent=2), 
                                              "raw_results.json", 
                                              "Download Raw JSON"),
                            unsafe_allow_html=True)
        else:
            st.info("Enter a search query and click 'Search' to begin.")

if __name__ == "__main__":
    main()
