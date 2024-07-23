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
    page_title="Search Results Analyzer", page_icon="🔍", layout="wide"
)

# Load the SerpAPI key and OpenRouter API key from the secrets file
SERPAPI_KEY = st.secrets["serpapi"]["api_key"]
OPENROUTER_API_KEY = st.secrets["openrouter"]["api_key"]

def fetch_search_results(query: str, num_results: int):
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
        "related_questions": [],
    }

    # Parse ads
    if "ads" in results:
        for item in results["ads"]:
            parsed_data["ads"].append(item)

    # Parse organic results
    if "organic_results" in results:
        for item in results["organic_results"]:
            parsed_data["organic"].append(item)

    # Parse shopping results
    if "shopping_results" in results:
        for item in results["shopping_results"]:
            parsed_data["shopping_results"].append(item)

    # Parse related questions
    if "related_questions" in results:
        for item in results["related_questions"]:
            parsed_data["related_questions"].append(item)

    return parsed_data

def analyze_row(row, query):
    prompt = f"""Analyze this search result for the query '{query}' and provide insights for digital marketing:

Result Type: {row['type']}
Full Data: {json.dumps(row, indent=2)}

Please provide a comprehensive analysis including:
1. Relevance to the search query
2. Key elements that make this result stand out
3. Suggested improvements for creating more effective content or ads based on this result
4. Target audience insights
5. Keyword analysis (list top 5 keywords)
6. Call-to-action effectiveness (if applicable)
7. Unique selling propositions (if applicable)
8. Competitive advantage analysis

Format your response as a JSON object with the following keys: relevance, key_elements, improvements, target_audience, keywords, cta_effectiveness, usp, competitive_advantage."""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are an expert digital marketing analyst specializing in search result analysis for '{query}'. Your goal is to provide insights that will help in creating better content and ads for this specific query.",
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

def process_results(parsed_data, query):
    all_results = []

    for result_type, data in parsed_data.items():
        for index, row in enumerate(data):
            with st.spinner(f"Analyzing {result_type.capitalize()} Result {index + 1}..."):
                row['type'] = result_type  # Add type to the row data
                analysis = analyze_row(row, query)
                all_results.append({
                    "Type": result_type,
                    "Position": index + 1,
                    "Title": row.get("title", "N/A"),
                    "Link": row.get("link", "N/A"),
                    "Original Data": json.dumps(row),
                    "Analysis": json.dumps(analysis)
                })

    return all_results

def display_results(results):
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False)
    st.download_button(
        label="Download Analysis as CSV",
        data=csv,
        file_name="search_results_analysis.csv",
        mime="text/csv",
        key="download_csv",
    )

def main():
    st.title("Search Results Analyzer")

    query = st.text_input("Enter search query:")
    num_results = st.slider("Number of results to fetch", min_value=1, max_value=100, value=10)

    if st.button("Analyze"):
        with st.spinner("Fetching and analyzing results..."):
            # Fetch search results
            results = fetch_search_results(query, num_results)
            
            if results:
                # Parse results
                parsed_data = parse_results(results)
                
                # Process and analyze results
                analyzed_results = process_results(parsed_data, query)
                
                # Display results
                st.subheader("Analysis Results")
                display_results(analyzed_results)
                
                # Display raw results
                with st.expander("Raw Search Results"):
                    st.json(results)
            else:
                st.error("No results to analyze. Please try a different query.")

if __name__ == "__main__":
    main()
