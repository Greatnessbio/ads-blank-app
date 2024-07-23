import streamlit as st
import pandas as pd
from serpapi import GoogleSearch

# Set page config
st.set_page_config(page_title="Secure Search Results Display", page_icon="🔍", layout="wide")

# Load the SerpAPI key and login credentials from the secrets
SERPAPI_KEY = st.secrets["serpapi"]["api_key"]
USERNAME = st.secrets["credentials"]["username"]
PASSWORD = st.secrets["credentials"]["password"]

def login():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username == USERNAME and password == PASSWORD:
            st.session_state["logged_in"] = True
            st.success("Logged in successfully!")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

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
        return results
    except Exception as e:
        st.error(f"Error fetching search results: {str(e)}")
        return {}

def display_results(results):
    # Display organic results
    if "organic_results" in results:
        st.subheader("Organic Results")
        df_organic = pd.DataFrame(results["organic_results"])
        st.dataframe(df_organic, use_container_width=True)

    # Display ads
    if "ads" in results:
        st.subheader("Ads")
        df_ads = pd.DataFrame(results["ads"])
        st.dataframe(df_ads, use_container_width=True)

    # Display shopping results
    if "shopping_results" in results:
        st.subheader("Shopping Results")
        df_shopping = pd.DataFrame(results["shopping_results"])
        st.dataframe(df_shopping, use_container_width=True)

    # Display related questions
    if "related_questions" in results:
        st.subheader("Related Questions")
        df_questions = pd.DataFrame(results["related_questions"])
        st.dataframe(df_questions, use_container_width=True)

def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login()
    else:
        st.title("Secure Search Results Display")

        query = st.text_input("Enter search query:")
        num_results = st.slider("Number of results to fetch", min_value=1, max_value=100, value=10)

        if st.button("Search"):
            with st.spinner("Fetching results..."):
                results = fetch_search_results(query, num_results)
                
                if results:
                    display_results(results)
                    
                    # Display raw results
                    with st.expander("Raw Search Results"):
                        st.json(results)
                else:
                    st.error("No results to display. Please try a different query.")
        
        if st.sidebar.button("Logout"):
            st.session_state["logged_in"] = False
            st.experimental_rerun()

if __name__ == "__main__":
    main()
