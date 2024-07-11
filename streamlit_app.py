import streamlit as st
import requests
import pandas as pd

# Set page config at the very beginning
st.set_page_config(page_title="Google Search Results Parser", page_icon="🔍", layout="wide")

# Load the SerpAPI key and credentials from the secrets file
SERPAPI_KEY = st.secrets.get("serpapi", {}).get("api_key")
USERNAME = "Sambino"
PASSWORD = st.secrets.get("credentials", {}).get("Sambino")

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
      "gl": "us"
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
  
  for ad in ads[:5]:
      parsed_data['ads'].append({
          'Type': 'Ad',
          'Position': ad.get('position'),
          'Title': ad.get('title'),
          'Link': ad.get('link'),
          'Displayed Link': ad.get('displayed_link'),
          'Description': ad.get('description'),
      })
  
  for result in organic_results[:5]:
      parsed_data['organic'].append({
          'Type': 'Organic',
          'Title': result.get('title'),
          'Link': result.get('link'),
          'Snippet': result.get('snippet')
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
      
      query = st.text_input("Enter search query:", "elisa kits il-6")
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
