import streamlit as st
import requests
import pandas as pd
from typing import Dict, List

# Set page config at the very beginning
st.set_page_config(page_title="Google Search Results Parser", page_icon="🔍", layout="wide")

# Use Streamlit's cache mechanism
@st.cache_resource
def load_serpapi():
  try:
      from serpapi import GoogleSearch
      st.success("SerpAPI imported successfully")
      return GoogleSearch
  except ImportError as e:
      st.error(f"Error importing SerpAPI: {e}")
      try:
          import serpapi
          st.warning(f"SerpAPI version: {serpapi.__version__}")
      except ImportError:
          st.error("SerpAPI is not installed")
      return None

GoogleSearch = load_serpapi()

# Load the SerpAPI key and credentials from the secrets file
SERPAPI_KEY = st.secrets.get("serpapi", {}).get("api_key")
USERNAME = "Sambino"
PASSWORD = st.secrets.get("credentials", {}).get("Sambino")

@st.cache_data(ttl=300)
def fetch_google_search_results(query: str) -> Dict:
  if GoogleSearch is None:
      st.error("SerpAPI is not available. Please check the installation.")
      return {}
  
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
      search = GoogleSearch(params)
      results = search.get_dict()
      return results
  except Exception as e:
      st.error(f"Error fetching search results: {str(e)}")
      return {}

# The rest of the code remains the same...

# (Include the parse_results, display_results_table, login, and main functions here)

if __name__ == "__main__":
  main()
