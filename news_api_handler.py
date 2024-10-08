import requests
import csv
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
NEWS_API_URL = 'https://newsapi.org/v2/top-headlines'
CSV_FILE_PATH = 'static/news_data.csv'

def fetch_and_write_news_to_csv():
    logging.debug("Fetching news from NewsAPI")
    yesterday = datetime.now() - timedelta(days=1)
    params = {
        'apiKey': NEWS_API_KEY,
        'language': 'en',
        'from': yesterday.isoformat(),
        'sortBy': 'popularity',
        'category': 'general',  # Focus on general news
        'sources': 'the-new-york-times,associated-press',  # Prefer specific sources
        'excludeDomains': 'buzzfeed.com,tmz.com,theverge.com,nypost.com'  # Exclude entertainment and less relevant sources
    }
    
    response = requests.get(NEWS_API_URL, params=params)
    news_data = response.json()
    logging.debug(f"NewsAPI response: {news_data}")
    
    logging.info("Writing CSV file...")
    with open(CSV_FILE_PATH, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['title', 'description', 'url', 'source', 'city', 'country', 'lat', 'lng']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for article in news_data.get('articles', []):
            logging.debug(f"Processing article: {article}")
            title = article.get('title', '') or ''
            description = article.get('description', '') or ''
            city, country, location = get_location_from_text(title + ' ' + description)
            writer.writerow({
                'title': title,
                'description': description,
                'url': article['url'],
                'source': article['source']['name'],
                'city': city,
                'country': country,
                'lat': location['lat'],
                'lng': location['lng']
            })
    
    logging.info("CSV file written successfully.")

def get_location_from_text(text):
    # Placeholder for location extraction logic
    # This function should be implemented or imported from another module
    return "Unknown", "Unknown", {'lat': 0, 'lng': 0}