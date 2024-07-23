import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import json

# Set page config
st.set_page_config(page_title="Google Search Results Analyzer", page_icon="🔍", layout="wide")

# Load the SerpAPI key and credentials from the secrets file
SERPAPI_KEY = st.secrets["serpapi"]["api_key"]
USERNAME = st.secrets["credentials"]["username"]
PASSWORD = st.secrets["credentials"]["password"]

def fetch_search_results(query: str, num_results: int):
    if not SERPAPI_KEY:
        st.error("SerpAPI key is missing. Please check your secrets.")
        return {}

    params = {
        "api_key": SERPAPI_KEY,
        "engine": "google",
        "q": query,
        "num": num_results,
        "location": "Austin, Texas, United States"
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        return results
    except Exception as e:
        st.error(f"Error fetching search results: {str(e)}")
        return {}

def display_results(results):
    # Display ads
    if "ads" in results:
        st.subheader("Ads")
        ads_df = pd.json_normalize(results["ads"])
        st.dataframe(ads_df, use_container_width=True)
        
        # Display full JSON for each ad
        for i, ad in enumerate(results["ads"]):
            with st.expander(f"Ad {i+1} Full JSON"):
                st.json(ad)

    # Display organic results
    if "organic_results" in results:
        st.subheader("Organic Results")
        organic_df = pd.json_normalize(results["organic_results"])
        st.dataframe(organic_df, use_container_width=True)
        
        # Display full JSON for each organic result
        for i, result in enumerate(results["organic_results"]):
            with st.expander(f"Organic Result {i+1} Full JSON"):
                st.json(result)

    # Display other relevant sections
    relevant_sections = [
        "related_questions", "related_searches", "pagination", 
        "serpapi_pagination", "search_information", "search_parameters"
    ]
    
    for section in relevant_sections:
        if section in results:
            st.subheader(section.replace("_", " ").title())
            st.json(results[section])

    # Display raw results
    with st.expander("Raw JSON Results"):
        st.json(results)

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
        st.title("Google Search Results Analyzer")

        query = st.text_input("Enter search query:")
        num_results = st.slider("Number of results to fetch", min_value=1, max_value=100, value=10)

        if st.button("Search"):
            with st.spinner("Fetching results..."):
                results = fetch_search_results(query, num_results)
                
                if results:
                    display_results(results)
                else:
                    st.error("No results to display. Please try a different query.")

        # Add information about the app
        st.sidebar.title("About")
        st.sidebar.info(
            "This app uses the SerpAPI to fetch Google search results "
            "and displays them in a comprehensive format, including ads, "
            "organic results, and other relevant information."
        )
        st.sidebar.title("Instructions")
        st.sidebar.info(
            "1. Enter your search query in the text box.\n"
            "2. Adjust the number of results to fetch using the slider.\n"
            "3. Click the 'Search' button to see the results.\n"
            "4. Explore the various sections of the search results."
        )

        if st.sidebar.button("Logout"):
            st.session_state["logged_in"] = False
            st.experimental_rerun()

if __name__ == "__main__":
    main()
