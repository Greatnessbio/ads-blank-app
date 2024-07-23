import streamlit as st
import requests
import pandas as pd
import json
from streamlit.logger import get_logger
import base64
from serpapi import GoogleSearch

LOGGER = get_logger(__name__)

# Set page config at the very beginning
st.set_page_config(
    page_title="Google Search Results Parser", page_icon="🔍", layout="wide"
)

# Load the SerpAPI key and credentials from the secrets file
SERPAPI_KEY = st.secrets["serpapi"]["api_key"]
USERNAME = st.secrets["credentials"]["username"]
PASSWORD = st.secrets["credentials"]["password"]

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
    "google_domain": "google.com",
    "location": "Austin,Texas,United States",
    "device": "desktop",
    "include_ads": "true",
}

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        LOGGER.info(f"Full API response: {json.dumps(results, indent=2)}")
        return results
    except Exception as e:
        st.error(f"Error fetching search results: {str(e)}")
        return {}

def parse_results(results):
    parsed_data = {
        "ads": [],
        "organic": [],
        "shopping_results": [],
        "immersive_products": [],
        "related_questions": [],
        "related_searches": [],
    }

    # Parse ads
    if "ads" in results:
        for item in results["ads"]:
            ad_data = {
                "Type": "Ad",
                "Position": item.get("position"),
                "Title": item.get("title"),
                "Link": item.get("link"),
                "Displayed Link": item.get("displayed_link"),
                "Description": item.get("description"),
                "Sitelinks": ", ".join(
                    [sitelink.get("title", "") for sitelink in item.get("sitelinks", [])]
                ),
                "Source": item.get("source"),
            }
            parsed_data["ads"].append(ad_data)

    # Parse organic results
    if "organic_results" in results:
        for result in results["organic_results"]:
            organic_data = {
                "Type": "Organic",
                "Position": result.get("position"),
                "Title": result.get("title"),
                "Link": result.get("link"),
                "Displayed Link": result.get("displayed_link"),
                "Snippet": result.get("snippet"),
                "Sitelinks": ", ".join(
                    [
                        sitelink.get("title", "")
                        for sitelink in result.get("sitelinks", {}).get("inline", [])
                    ]
                ),
                "Source": result.get("source"),
            }
            parsed_data["organic"].append(organic_data)

    # Parse shopping results
    if "shopping_results" in results:
        for item in results["shopping_results"]:
            shopping_data = {
                "Type": "Shopping",
                "Position": item.get("position"),
                "Title": item.get("title"),
                "Link": item.get("link"),
                "Price": item.get("price"),
                "Source": item.get("source"),
                "Rating": item.get("rating"),
                "Reviews": item.get("reviews"),
            }
            parsed_data["shopping_results"].append(shopping_data)

    # Parse immersive products
    if "immersive_products" in results:
        for item in results["immersive_products"]:
            immersive_data = {
                "Type": "Immersive Product",
                "Title": item.get("title"),
                "Link": item.get("link"),
                "Price": item.get("price"),
                "Source": item.get("source"),
            }
            parsed_data["immersive_products"].append(immersive_data)

    # Parse related questions
    if "related_questions" in results:
        for item in results["related_questions"]:
            question_data = {
                "Type": "Related Question",
                "Question": item.get("question"),
                "Snippet": item.get("snippet"),
                "Title": item.get("title"),
                "Link": item.get("link"),
            }
            parsed_data["related_questions"].append(question_data)

    # Parse related searches
    if "related_searches" in results:
        for item in results["related_searches"]:
            search_data = {
                "Type": "Related Search",
                "Query": item.get("query"),
                "Link": item.get("link"),
            }
            parsed_data["related_searches"].append(search_data)

    return parsed_data

def display_results_table(parsed_data):
    for result_type, data in parsed_data.items():
        if data:
            st.subheader(f"{result_type.capitalize().replace('_', ' ')} Results")
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info(f"No {result_type.replace('_', ' ')} results found.")

def dataframe_to_markdown(df):
    markdown = "| " + " | ".join(df.columns) + " |\n"
    markdown += "| " + " | ".join(["---" for _ in df.columns]) + " |\n"
    
    for _, row in df.iterrows():
        markdown += "| " + " | ".join(str(value) for value in row) + " |\n"
    
    return markdown

def generate_report(query, parsed_data):
    report = f"# Search Results Analysis for '{query}'\n\n"

    for result_type, data in parsed_data.items():
        if data:
            report += f"## {result_type.capitalize().replace('_', ' ')} Results\n\n"
            df = pd.DataFrame(data)
            report += dataframe_to_markdown(df)
            report += "\n\n"

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

        query = st.text_input("Enter search query:")
        num_results = st.slider(
            "Number of results to fetch", min_value=1, max_value=100, value=10
        )

        search_button = st.button("Search")

        if search_button or "parsed_data" in st.session_state:
            if search_button:
                with st.spinner("Fetching results..."):
                    results = fetch_google_search_results(query, num_results)
                    parsed_data = parse_results(results)
                    st.session_state.parsed_data = parsed_data
                    st.session_state.raw_results = results
            else:
                parsed_data = st.session_state.parsed_data
                results = st.session_state.raw_results

            st.subheader("Search Information")
            st.write(
                f"Total results: {results.get('search_information', {}).get('total_results', 'N/A')}"
            )
            st.write(
                f"Time taken: {results.get('search_information', {}).get('time_taken_displayed', 'N/A')} seconds"
            )

            display_results_table(parsed_data)

            # Generate and provide download link for the report
            report = generate_report(query, parsed_data)
            report_bytes = report.encode("utf-8")
            st.download_button(
                label="Download Full Report (Markdown)",
                data=report_bytes,
                file_name="search_results_analysis.md",
                mime="text/markdown",
                key="download_report",
            )

            # Raw JSON Results in a collapsible section with download option
            with st.expander("Raw JSON Results"):
                st.json(results)
                st.markdown(
                    get_download_link(
                        json.dumps(results, indent=2),
                        "raw_results.json",
                        "Download Raw JSON",
                    ),
                    unsafe_allow_html=True,
                )

if __name__ == "__main__":
    main()
