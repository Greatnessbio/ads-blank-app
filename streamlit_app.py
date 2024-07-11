import streamlit as st
import requests
import pandas as pd

# Add error handling for SerpAPI import
try:
  from serpapi import GoogleSearch
  print(f"SerpAPI imported successfully")
except ImportError as e:
  print(f"Error importing SerpAPI: {e}")
  try:
      import serpapi
      print(f"SerpAPI version: {serpapi.__version__}")
  except ImportError:
      print("SerpAPI is not installed")

# Load the SerpAPI key and credentials from the secrets file
SERPAPI_KEY = st.secrets["serpapi"]["api_key"]
USERNAME = "Sambino"  # This is the username from your secrets
PASSWORD = st.secrets["credentials"]["Sambino"]  # This is the password for Sambino

def fetch_google_search_results(query):
  params = {
      "engine": "google",
      "q": query,
      "api_key": SERPAPI_KEY
  }
  try:
      search = GoogleSearch(params)
      results = search.get_dict()
      return results
  except NameError:
      st.error("GoogleSearch is not available. Please check SerpAPI installation.")
      return {}

def parse_results(results):
  ads = results.get('ads', [])
  organic_results = results.get('organic_results', [])
  
  parsed_ads = []
  for ad in ads[:5]:
      parsed_ads.append({
          'Type': 'Ad',
          'Title': ad.get('title'),
          'Link': ad.get('link'),
          'Snippet': ad.get('snippet')
      })
  
  parsed_results = []
  for result in organic_results[:5]:
      parsed_results.append({
          'Type': 'Organic',
          'Title': result.get('title'),
          'Link': result.get('link'),
          'Snippet': result.get('snippet')
      })
  
  return parsed_ads + parsed_results

def display_results_table(parsed_data):
  df = pd.DataFrame(parsed_data)
  st.dataframe(df)

def login():
  st.title("Login")
  username = st.text_input("Username")
  password = st.text_input("Password", type="password")
  if st.button("Login"):
      if username == USERNAME and password == PASSWORD:
          st.session_state["logged_in"] = True
          st.success("Logged in successfully!")
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
