from flask import Flask, render_template
import os
import logging
import polars as pl
from great_tables import GT
from news_api_handler import fetch_news_data, augment_news_data, CSV_DIR_PATH

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Ensure the static directory exists
os.makedirs('static', exist_ok=True)

@app.route('/')
def index():
    logging.debug("Starting index route")

    # This will fetch the news data and write it to a CSV file
    fetch_news_data()

    # Augment the news data
    augment_news_data()

    # Get the newest CSV file
    csv_file_path = get_newest_csv_file()

    # Generate the HTML table from the CSV file
    table_html = make_table_from_csv(csv_file_path)

    # Render the HTML template with the table
    return render_template('index.html', table_html=table_html)

def get_newest_csv_file():
    logging.debug("Selecting the newest CSV file")
    csv_files = sorted(
        [f for f in os.listdir(CSV_DIR_PATH) if f.startswith('news_data_') and f.endswith('.csv')],
        key=lambda x: os.path.getmtime(os.path.join(CSV_DIR_PATH, x)),
        reverse=True
    )
    if csv_files:
        newest_file = os.path.join(CSV_DIR_PATH, csv_files[0])
        logging.info(f"Newest CSV file selected: {newest_file}")
        return newest_file
    else:
        logging.warning("No CSV files found")
        return None

def make_table_from_csv(csv_file_path):
    if not csv_file_path:
        logging.error("No CSV file path provided")
        return "<p>No data available</p>"
    
    logging.debug(f"Reading CSV file to create HTML table: {csv_file_path}")
    table = pl.read_csv(csv_file_path)
    gt_table = (
        GT(table)
        #.cols_hide(columns=["uri", "geolocation", "city", "country"])
    )
    
    table_html = gt_table.as_raw_html()
    logging.debug("HTML table created")
    return table_html

if __name__ == '__main__':
    logging.info("Starting Flask app")
    app.run(debug=True)