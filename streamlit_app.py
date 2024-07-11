import streamlit as st
import requests
import pandas as pd
import json
import re
from streamlit.logger import get_logger
from collections import Counter
import plotly.express as px
import base64
from io import BytesIO

LOGGER = get_logger(__name__)

# Set page config at the very beginning
st.set_page_config(page_title="Advanced Google Search Results Analyzer", page_icon="🔍", layout="wide")

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
        "gl": "us",
        "num": 10  # Limit to 10 results
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
    
    for ad in ads[:10]:  # Limit to 10 ads
        parsed_data['ads'].append({
            'Type': 'Ad',
            'Position': ad.get('position'),
            'Title': ad.get('title'),
            'Link': ad.get('link'),
            'Displayed Link': ad.get('displayed_link'),
            'Description': ad.get('description'),
        })
    
    for result in organic_results[:10]:  # Limit to 10 organic results
        parsed_data['organic'].append({
            'Type': 'Organic',
            'Position': result.get('position'),
            'Title': result.get('title'),
            'Link': result.get('link'),
            'Snippet': result.get('snippet'),
            'Featured Snippet': result.get('featured_snippet', {}).get('snippet', '')
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

    result_type = "ad" if row['Type'] == 'Ad' else "organic search result"
    
    prompt = f"""Analyze this {result_type} data and provide detailed insights for digital marketing:

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

def process_results(results):
    df_ads = pd.DataFrame(results['ads'])
    df_organic = pd.DataFrame(results['organic'])
    
    if 'analyzed_results' not in st.session_state:
        st.session_state.analyzed_results = {}
    
    for index, row in df_ads.iterrows():
        if f"ad_{index}" not in st.session_state.analyzed_results:
            analysis = analyze_row(row)
            st.session_state.analyzed_results[f"ad_{index}"] = analysis
        
        st.write(f"Ad Result {index + 1}:")
        st.write(row)
        st.write("Analysis:")
        st.write(st.session_state.analyzed_results[f"ad_{index}"])
        st.write("---")
    
    for index, row in df_organic.iterrows():
        if f"organic_{index}" not in st.session_state.analyzed_results:
            analysis = analyze_row(row)
            st.session_state.analyzed_results[f"organic_{index}"] = analysis
        
        st.write(f"Organic Result {index + 1}:")
        st.write(row)
        st.write("Analysis:")
        st.write(st.session_state.analyzed_results[f"organic_{index}"])
        st.write("---")

def simple_keyword_extraction(text):
    words = re.findall(r'\b\w+\b', text.lower())
    return [word for word in words if len(word) > 2]

def analyze_keywords(parsed_data):
    all_text = ' '.join([result.get('Title', '') + ' ' + result.get('Description', '') + ' ' + result.get('Snippet', '') for result in parsed_data['ads'] + parsed_data['organic']])
    keywords = simple_keyword_extraction(all_text)
    keyword_freq = Counter(keywords)
    return keyword_freq.most_common(20)

def visualize_keyword_frequency(keyword_freq):
    df = pd.DataFrame(keyword_freq, columns=['Keyword', 'Frequency'])
    fig = px.bar(df, x='Keyword', y='Frequency', title='Top 20 Keywords')
    st.plotly_chart(fig)

def analyze_competitor_domains(parsed_data):
    domains = [re.search(r'(?:https?://)?(?:www\.)?([^/]+)', result['Link']).group(1) if result['Link'] else '' for result in parsed_data['ads'] + parsed_data['organic']]
    domain_freq = Counter(domains)
    return domain_freq.most_common(10)

def visualize_competitor_domains(domain_freq):
    df = pd.DataFrame(domain_freq, columns=['Domain', 'Frequency'])
    fig = px.pie(df, values='Frequency', names='Domain', title='Top 10 Competitor Domains')
    st.plotly_chart(fig)

def generate_report(parsed_data, keyword_freq, domain_freq):
    report = "# Google Search Results Analysis Report\n\n"
    
    report += "## Ad Results\n\n"
    for index, ad in enumerate(parsed_data['ads']):
        report += f"### Ad Result {index + 1}\n\n"
        for key, value in ad.items():
            report += f"**{key}:** {value}\n\n"
        if f"ad_{index}" in st.session_state.analyzed_results:
            report += f"**Analysis:**\n\n{st.session_state.analyzed_results[f'ad_{index}']}\n\n"
        report += "---\n\n"
    
    report += "## Organic Results\n\n"
    for index, result in enumerate(parsed_data['organic']):
        report += f"### Organic Result {index + 1}\n\n"
        for key, value in result.items():
            report += f"**{key}:** {value}\n\n"
        if f"organic_{index}" in st.session_state.analyzed_results:
            report += f"**Analysis:**\n\n{st.session_state.analyzed_results[f'organic_{index}']}\n\n"
        report += "---\n\n"
    
    report += "## Keyword Analysis\n\n"
    report += "| Keyword | Frequency |\n|---------|-----------|\n"
    for keyword, freq in keyword_freq:
        report += f"| {keyword} | {freq} |\n"
    
    report += "\n## Competitor Domain Analysis\n\n"
    report += "| Domain | Frequency |\n|--------|-----------|\n"
    for domain, freq in domain_freq:
        report += f"| {domain} | {freq} |\n"
    
    return report

def get_table_download_link(df, filename, linktext):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{linktext}</a>'
    return href

def get_report_download_link(report, filename, linktext):
    b64 = base64.b64encode(report.encode()).decode()
    href = f'<a href="data:file/markdown;base64,{b64}" download="{filename}">{linktext}</a>'
    return href

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
        st.title("Advanced Google Search Results Analyzer")
        
        query = st.text_input("Enter search query:", "elisa kits il-6")
        search_button = st.button("Analyze")
        
        if search_button:
            with st.spinner("Fetching and analyzing results..."):
                results = fetch_google_search_results(query)
                parsed_data = parse_results(results)
                
                st.subheader("Search Information")
                st.write(f"Total results: {results.get('search_information', {}).get('total_results', 'N/A')}")
                st.write(f"Time taken: {results.get('search_information', {}).get('time_taken_displayed', 'N/A')} seconds")
                
                display_results_table(parsed_data)
                
                st.subheader("Keyword Analysis")
                keyword_freq = analyze_keywords(parsed_data)
                visualize_keyword_frequency(keyword_freq)
                
                st.subheader("Competitor Domain Analysis")
                domain_freq = analyze_competitor_domains(parsed_data)
                visualize_competitor_domains(domain_freq)
                
                st.subheader("Detailed Result Analysis")
                process_results(parsed_data)
                
                # Generate and provide download links for reports
                report = generate_report(parsed_data, keyword_freq, domain_freq)
                st.markdown(get_report_download_link(report, "search_analysis_report.md", "Download Full Report (Markdown)"), unsafe_allow_html=True)
                
                df_ads = pd.DataFrame(parsed_data['ads'])
                df_organic = pd.DataFrame(parsed_data['organic'])
                st.markdown(get_table_download_link(df_ads, "ad_results.csv", "Download Ad Results (CSV)"), unsafe_allow_html=True)
                st.markdown(get_table_download_link(df_organic, "organic_results.csv", "Download Organic Results (CSV)"), unsafe_allow_html=True)
                
                st.subheader("Raw JSON Results")
                st.json(results)

        if st.button("Show Stored Analyses"):
            for key, analysis in st.session_state.analyzed_results.items():
                result_type = "Ad" if key.startswith("ad_") else "Organic"
                index = key.split("_")[1]
                st.write(f"Analysis for {result_type} Result {int(index) + 1}:")
                st.write(analysis)
                st.write("---")

if __name__ == "__main__":
    main()
