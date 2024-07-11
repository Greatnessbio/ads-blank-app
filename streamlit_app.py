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
SERPAPI_KEY = st.secrets["serpapi"]["api_key"]
USERNAME = "Sambino"
PASSWORD = st.secrets["credentials"]["Sambino"]

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_google_search_results(query: str) -> Dict:
  if GoogleSearch is None:
      st.error("SerpAPI is not available. Please check the installation.")
      return {}
  
  params = {
      "engine": "google",
      "q": query,
      "api_key": SERPAPI_KEY
  }
  try:
      search = GoogleSearch(params)
      results = search.get_dict()
      return results
  except Exception as e:
      st.error(f"Error fetching search results: {e}")
      return {}

def parse_results(results: Dict) -> List[Dict]:
  ads = results.get('ads', [])
  organic_results = results.get('organic_results', [])
  
  parsed_data = []
  for ad in ads[:5]:
      parsed_data.append({
          'Type': 'Ad',
          'Title': ad.get('title'),
          'Link': ad.get('link'),
          'Snippet': ad.get('snippet')
      })
  
  for result in organic_results[:5]:
      parsed_data.append({
          'Type': 'Organic',
          'Title': result.get('title'),
          'Link': result.get('link'),
          'Snippet': result.get('snippet')
      })
  
  return parsed_data

def display_results_table(parsed_data: List[Dict]):
  df = pd.DataFrame(parsed_data)
  st.dataframe(df, use_container_width=True)

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
      
      query = st.text_input("Enter search query:", "elisa kits for il6")
      
      if st.button("Search"):
          with st.spinner("Fetching results..."):
              results = fetch_google_search_results(query)
              parsed_data = parse_results(results)
              display_results_table(parsed_data)

if __name__ == "__main__":
  main()
