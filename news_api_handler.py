import requests
import csv
import os
from io import StringIO
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import polars as pl
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

NYTIMES_API_KEY = os.getenv('NYTIMES_API_KEY')
NYTIMES_API_URL = "https://api.nytimes.com/svc/topstories/v2"
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CSV_DIR_PATH = "static/csv_files"

# Ensure the CSV directory exists
os.makedirs(CSV_DIR_PATH, exist_ok=True)

def fetch_news_data(max_articles=60, time_threshold_minutes=30):
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
    
    sections = ["world", "us", "politics", "sports", "movies", "science", "technology"]
    articles = []
    
    for section in sections:
        params = {
            "api-key": NYTIMES_API_KEY
        }
        response = requests.get(f"{NYTIMES_API_URL}/{section}.json", params=params)
        section_data = response.json()
        logging.debug(f"NY Times API response for {section}: {section_data}")
        
        if "results" in section_data:
            articles.extend(section_data["results"])
        else:
            logging.error(f"Unexpected response structure for section {section}")
    
    # Limit the number of articles processed
    articles = articles[:max_articles]
    
    # Generate a timestamped filename for the CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file_path = os.path.join(CSV_DIR_PATH, f'news_data_{timestamp}.csv')
    
    logging.info(f"Writing CSV file: {csv_file_path}")
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csvfile:
        
        fieldnames = ["uri", "title", "description", "url", "published_date", "source", "geolocation"]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for article in articles:
            logging.debug(f"Processing article: {article}")
            if isinstance(article, dict):

                # Get the uri so it serves as a unique identifier
                uri = article.get("uri", "")

                # If the `item_type` is not "Article", skip the article
                if article.get("item_type") != "Article":
                    logging.debug(f"Skipping non-article item: {article}")
                    continue

                # Get the country from the first `geo_facet` item;
                # if not present then skip the article
                geolocation = article.get("geo_facet", [""])[0] if article.get("geo_facet") else ""

                # Don't keep an article that doesn't have any geolocation info
                if not geolocation:
                    logging.debug(f"Skipping article without any location information: {article}")
                    continue

                title = article.get("title", "") or ""
                description = article.get("abstract", "") or ""
                url = article.get("url", "")
                published_date = article.get("published_date", "")
                source = "New York Times"

                writer.writerow({
                    "uri": uri,
                    "title": title,
                    "description": description,
                    "url": url,
                    "published_date": published_date,
                    "source": source,
                    "geolocation": geolocation
                })
            else:
                logging.error(f"Unexpected article format: {article}")
    
    logging.info("CSV file written successfully.")

def augment_news_data():
    logging.debug("Augmenting news data")

    # Get the newest CSV file
    csv_file_path = get_newest_csv_file()

    # Load OPENAI_API_KEY from the .env file
    load_dotenv()

    # Create an OpenAI client
    client = OpenAI()

    # Read the CSV file into a Polars table
    tbl_data = pl.read_csv(csv_file_path)

    # If the DataFrame has the columns "latitude", and "longitude", then skip the augmentation
    if "latitude" in tbl_data.columns and "longitude" in tbl_data.columns:
        logging.info("DataFrame already has the required columns. Skipping augmentation.")
        return
    
    # Select the columns we need for conversion to JSON
    tbl_data_selected = tbl_data.select(["uri", "title", "description", "geolocation"])
    
    # Convert the Polars table to JSON
    tbl_json = tbl_data_selected.write_json()

    # The prompt for the OpenAI API will be provided as a series of messages that guide the
    # model toward providing a consistent JSON blob with new fields that are important to the
    # application and are difficult to generate through conventional code
    messages = [
        {"role": "system", "content": "You are an expert at surmising the geolocation of a news story when"
    "provided with only the title of the news story, a short summary of the story, and an unstructured"
    "location name (could be a country, a city within a country, etc.)."},
    {"role": "user", "content": f"""
    I'm providing JSON text with the schema: 'uri', 'title',
    'description', and 'geolocation'. Each member is a record of a news story. What I need is the
    city and the country associated with the news story. If you cannot guess the city or its not
    clear, use the capital city of the country. The country needs to be short, standardized versions
    of the country name in English (e.g., 'United States', 'United Kingdom', 'South Korea', etc.).
    I will pass in the JSON data after the break
    ----
    {tbl_json}
    ----
    What I need returned is a JSON string with the same number of records in the same order as the
    input. The fields required are: 'city', 'country', 'latitude', and 'longitude'. I would also like
    the input 'uri' field to be included so that I can join the returned JSON with the complete
    dataset (that 'uri' field will serve as an ID for each member.

    One last thing, be sure to give me just the JSON string without any conversational text before
    and after. I want to be sure I can depend on your output as consistent input for my processing.
    """},
    ]

    # Call out to the OpenAI API to generate a response.
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )

    response_json = response.choices[0].message.content

    # Remove the fenced code block text (if present) from the response
    response_json = response_json.replace("```json\n", "").replace("\n```", "")

    # Write the augmented data to the same CSV file through a join on the "uri" field
    tbl_augmented = pl.read_json(StringIO(response_json))
    tbl_augmented = tbl_augmented.select(["uri", "city", "country", "latitude", "longitude"])
    tbl_complete = tbl_data.join(tbl_augmented, on="uri", how="left")
    tbl_complete.write_csv(csv_file_path)


def get_newest_csv_file():
    logging.debug("Selecting the newest CSV file")
    csv_files = sorted(
        [os.path.join(CSV_DIR_PATH, f) for f in os.listdir(CSV_DIR_PATH) if f.startswith("news_data_") and f.endswith(".csv")],
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
        [f for f in os.listdir(CSV_DIR_PATH) if f.startswith("news_data_") and f.endswith(".csv")],
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
