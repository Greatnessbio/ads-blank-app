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
      import serpapi
      st.success(f"SerpAPI imported successfully. Version: {serpapi.__version__}")
      return serpapi
  except ImportError as e:
      st.error(f"Error importing SerpAPI: {e}")
      return None

serpapi = load_serpapi()

# Load the SerpAPI key and credentials from the secrets file
SERPAPI_KEY = st.secrets.get("serpapi", {}).get("api_key")
USERNAME = "Sambino"
PASSWORD = st.secrets.get("credentials", {}).get("Sambino")

@st.cache_data(ttl=300)
def fetch_google_search_results(query: str) -> Dict:
  if serpapi is None:
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
      search = serpapi.GoogleSearch(params)
      results = search.get_dict()
      return results
  except Exception as e:
      st.error(f"Error fetching search results: {str(e)}")
      return {}

def parse_results(results: Dict) -> Dict[str, List[Dict]]:
  ads = results.get('ads', [])
  organic_results = results.get('organic_results', [])
  
  parsed_data = {
      'ads': [],
      'organic': []
  }
  
  for ad in ads[:5]:
      parsed_data['ads'].append({
          'Type': 'Ad',
          'Position': ad.get('position'),
          'Block Position': ad.get('block_position'),
          'Title': ad.get('title'),
          'Link': ad.get('link'),
          'Displayed Link': ad.get('displayed_link'),
          'Tracking Link': ad.get('tracking_link'),
          'Thumbnail': ad.get('thumbnail'),
          'Description': ad.get('description'),
          'Extensions': ', '.join(ad.get('extensions', [])),
          'Sitelinks': [link.get('title') for link in ad.get('sitelinks', [])],
          'Price': ad.get('price'),
          'Rating': ad.get('rating'),
          'Reviews': ad.get('reviews'),
          'Source': ad.get('source')
      })
  
  for result in organic_results[:5]:
      parsed_data['organic'].append({
          'Type': 'Organic',
          'Title': result.get('title'),
          'Link': result.get('link'),
          'Snippet': result.get('snippet')
      })
  
  return parsed_data

def display_results_table(parsed_data: Dict[str, List[Dict]]):
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
      
      col1, col2 = st.columns([3, 1])
      with col1:
          query = st.text_input("Enter search query:", "elisa kits")
      with col2:
          search_button = st.button("Search")
      
      if search_button:
          with st.spinner("Fetching results..."):
              results = fetch_google_search_results(query)
              parsed_data = parse_results(results)
              
              st.subheader("Search Information")
              st.write(f"Total results: {results.get('search_information', {}).get('total_results', 'N/A')}")
              st.write(f"Time taken: {results.get('search_information', {}).get('time_taken_displayed', 'N/A')} seconds")
              
              display_results_table(parsed_data)
              
              st.subheader("Raw JSON Results")
              st.json(results)

if __name__ == "__main__":
  main()
