from flask import Flask, render_template
import openai
from great_tables import GT
import polars as pl
import os
import logging
from news_api_handler import fetch_and_write_news_to_csv

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Ensure the static directory exists
os.makedirs('static', exist_ok=True)

openai.api_key = OPENAI_API_KEY

@app.route('/')
def index():
    logging.debug("Starting index route")
    fetch_and_write_news_to_csv()
    table_html = make_table_from_csv()
    return render_template('index.html', table_html=table_html)

def make_table_from_csv():
    logging.debug("Reading CSV file to create HTML table")
    table = pl.read_csv('static/news_data.csv')
    gt_table = GT(table)
    
    table_html = gt_table.as_raw_html()
    logging.debug("HTML table created")
    return table_html

if __name__ == '__main__':
    logging.info("Starting Flask app")
    app.run(debug=True)