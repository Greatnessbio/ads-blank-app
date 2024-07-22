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


def parse_results(results, num_results):
    parsed_data = {
        "ads": [],
        "organic": [],
        "shopping_results": [],
        "immersive_products": [],
    }

    # Parse ads
    if "ads" in results:
        for item in results["ads"][:num_results]:
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
        for result in results["organic_results"][:num_results]:
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
        for item in results["shopping_results"][:num_results]:
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
        for item in results["immersive_products"][:num_results]:
            immersive_data = {
                "Type": "Immersive Product",
                "Title": item.get("title"),
                "Link": item.get("link"),
                "Price": item.get("price"),
                "Source": item.get("source"),
            }
            parsed_data["immersive_products"].append(immersive_data)

    return parsed_data


@st.cache_data(ttl=3600)
def analyze_row(_row, api_key, original_json):
    result_type = _row["Type"].lower()
    original_data = next(
        (
            item
            for item in original_json.get(f"{result_type}s", [])
            if str(item.get("position")) == str(_row.get("Position"))
        ),
        {},
    )

    prompt = f"""Analyze this search result data for the query 'elisa kits' and provide insights for digital marketing:

Result Type: {_row['Type']}
Title: {_row['Title']}
Link: {_row['Link']}
Position: {_row['Position']}
Full Data: {json.dumps(_row, indent=2)}

Original Data: {json.dumps(original_data, indent=2)}

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
Format your response as a JSON object with the following keys: seo_analysis, content_strategy, keywords, competitive_positioning, improvements, usp, cta_effectiveness, target_audience, recommendations."""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert digital marketing analyst specializing in SEO, PPC, and competitive analysis for scientific and medical products, particularly ELISA kits.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        analysis = response.json()["choices"][0]["message"]["content"]
        return json.loads(analysis)
    except requests.RequestException as e:
        LOGGER.error(f"API request failed: {e}")
        return {"error": f"Failed to analyze row: {str(e)}"}
    except (KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
        LOGGER.error(f"Error processing API response: {e}")
        return {"error": f"Error processing the analysis: {str(e)}"}


def process_results(parsed_data, original_json):
    api_key = load_api_key()
    if not api_key:
        st.error("API key not found.")
        return

    all_results = []  # Initialize the list here

    for result_type, data in parsed_data.items():
        if data:
            for index, row in enumerate(data):
                with st.spinner(
                    f"Analyzing {result_type.capitalize().replace('_', ' ')} Result {index + 1}..."
                ):
                    analysis = analyze_row(row, api_key, original_json)
                    all_results.append(
                        {
                            "Type": result_type,
                            "Position": row.get("Position"),
                            "Title": row.get("Title"),
                            "Link": row.get("Link"),
                            "Original Data": json.dumps(row),
                            "Analysis": json.dumps(analysis),
                        }
                    )

    st.session_state.analyzed_results = all_results


def display_results_table(parsed_data):
    for result_type, data in parsed_data.items():
        if data:
            st.subheader(f"{result_type.capitalize().replace('_', ' ')} Results")
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info(f"No {result_type.replace('_', ' ')} results found.")


def display_results():
    if (
        "analyzed_results" not in st.session_state
        or not st.session_state.analyzed_results
    ):
        st.warning("No analysis results available. Please run the analysis first.")
        return

    df = pd.DataFrame(st.session_state.analyzed_results)
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False)
    st.download_button(
        label="Download Analysis as CSV",
        data=csv,
        file_name="search_results_analysis.csv",
        mime="text/csv",
        key="download_csv",
    )


def generate_report(query, analyzed_results):
    report = f"# Search Results Analysis for '{query}'\n\n"

    for result in analyzed_results:
        report += f"## {result['Type']} Result - Position {result['Position']}\n\n"
        report += f"**Title:** {result['Title']}\n"
        report += f"**Link:** {result['Link']}\n\n"

        analysis = json.loads(result["Analysis"])
        report += f"### SEO Analysis\n{analysis.get('seo_analysis', 'N/A')}\n\n"
        report += (
            f"### Content Strategy\n{analysis.get('content_strategy', 'N/A')}\n\n"
        )
        report += f"### Keywords\n{', '.join(analysis.get('keywords', ['N/A']))}\n\n"
        report += (
            f"### Competitive Positioning\n{analysis.get('competitive_positioning', 'N/A')}\n\n"
        )
        report += f"### Improvements\n{analysis.get('improvements', 'N/A')}\n\n"
        report += (
            f"### Unique Selling Proposition\n{analysis.get('usp', 'N/A')}\n\n"
        )
        report += (
            f"### Call-to-Action Effectiveness\n{analysis.get('cta_effectiveness', 'N/A')}\n\n"
        )
        report += f"### Target Audience\n{analysis.get('target_audience', 'N/A')}\n\n"
        report += f"### Recommendations\n{analysis.get('recommendations', 'N/A')}\n\n"
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

        query = st.text_input("Enter search query:", "elisa kits")
        num_results = st.slider(
            "Number of results to fetch", min_value=1, max_value=10, value=5
        )

        search_button = st.button("Search")

        if search_button or "parsed_data" in st.session_state:
            if search_button:
                with st.spinner("Fetching results..."):
                    results = fetch_google_search_results(query, num_results)
                    parsed_data = parse_results(results, num_results)
                    st.session_state.parsed_data = parsed_data
                    st.session_state.raw_results = results
                    if "analyzed_results" in st.session_state:
                        del st.session_state.analyzed_results  # Clear previous analyses
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

            if st.button("Analyze Results", key="analyze_button"):
                process_results(parsed_data, results)

            display_results()

            # Generate and provide download link for the report
            if (
                "analyzed_results" in st.session_state
                and st.session_state.analyzed_results
            ):
                report = generate_report(query, st.session_state.analyzed_results)
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
