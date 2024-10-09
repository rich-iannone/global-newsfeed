import requests
import csv
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

NYTIMES_API_KEY = os.getenv('NYTIMES_API_KEY')
NYTIMES_API_URL = 'https://api.nytimes.com/svc/topstories/v2'
CSV_DIR_PATH = 'static/csv_files'  # Directory to store CSV files

# Ensure the CSV directory exists
os.makedirs(CSV_DIR_PATH, exist_ok=True)

def fetch_news_data(max_articles=10, time_threshold_minutes=10):
    logging.debug("Fetching news from New York Times API")
    
    if not NYTIMES_API_KEY:
        logging.error("New York Times API key is not set. Please check your .env file.")
        return
    
    # Check the latest CSV file's timestamp
    latest_csv_file = get_newest_csv_file()
    if latest_csv_file:
        latest_file_time = datetime.fromtimestamp(os.path.getmtime(latest_csv_file))
        time_difference = datetime.now() - latest_file_time
        if time_difference < timedelta(minutes=time_threshold_minutes):
            logging.info(f"Latest CSV file is recent ({time_difference} ago). Skipping new fetch.")
            return
    else:
        logging.info("No CSV files found. Fetching new data immediately.")
    
    sections = ['world', 'us']
    articles = []
    
    for section in sections:
        params = {
            'api-key': NYTIMES_API_KEY
        }
        response = requests.get(f"{NYTIMES_API_URL}/{section}.json", params=params)
        section_data = response.json()
        logging.debug(f"NY Times API response for {section}: {section_data}")
        
        if 'results' in section_data:
            articles.extend(section_data['results'])
        else:
            logging.error(f"Unexpected response structure for section {section}")
    
    # Limit the number of articles processed
    articles = articles[:max_articles]
    
    # Generate a timestamped filename for the CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file_path = os.path.join(CSV_DIR_PATH, f'news_data_{timestamp}.csv')
    
    logging.info(f"Writing CSV file: {csv_file_path}")
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['title', 'description', 'url', 'source', 'country']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for article in articles:
            logging.debug(f"Processing article: {article}")
            if isinstance(article, dict):
                title = article.get('title', '') or ''
                description = article.get('abstract', '') or ''
                url = article.get('url', '')
                source = 'New York Times'
                country = 'US' if section == 'us' else 'World'
                writer.writerow({
                    'title': title,
                    'description': description,
                    'url': url,
                    'source': source,
                    'country': country
                })
            else:
                logging.error(f"Unexpected article format: {article}")
    
    logging.info("CSV file written successfully.")

def get_newest_csv_file():
    logging.debug("Selecting the newest CSV file")
    csv_files = sorted(
        [os.path.join(CSV_DIR_PATH, f) for f in os.listdir(CSV_DIR_PATH) if f.startswith('news_data_') and f.endswith('.csv')],
        key=lambda x: os.path.getmtime(x),
        reverse=True
    )
    if csv_files:
        newest_file = csv_files[0]
        logging.info(f"Newest CSV file selected: {newest_file}")
        return newest_file
    else:
        logging.warning("No CSV files found")
        return None

def cull_old_csv_files(max_files=5):
    logging.debug("Culling old CSV files")
    now = datetime.now()
    csv_files = sorted(
        [f for f in os.listdir(CSV_DIR_PATH) if f.startswith('news_data_') and f.endswith('.csv')],
        key=lambda x: os.path.getmtime(os.path.join(CSV_DIR_PATH, x))
    )
    
    for file in csv_files:
        file_path = os.path.join(CSV_DIR_PATH, file)
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        if (now - file_mtime) > timedelta(hours=24):
            os.remove(file_path)
            logging.info(f"Removed old CSV file: {file}")
        elif len(csv_files) > max_files:
            os.remove(file_path)
            logging.info(f"Removed excess CSV file: {file}")
            csv_files.remove(file)