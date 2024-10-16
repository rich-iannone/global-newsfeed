from flask import Flask, render_template
import os
import time
import logging
import polars as pl
from great_tables import GT, google_font
from news_api_handler import cull_old_csv_files, fetch_news_data, augment_news_data, CSV_DIR_PATH

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

    # Cull old CSV files
    cull_old_csv_files()

    # This will fetch the news data and write it to a CSV file; here we are relying on the
    # news API to constantly provide fresh articles, so, only the most recent file is needed
    # for the application to function
    fetch_news_data(max_articles=100, time_threshold_minutes=10)

    # Add a small sleep here
    time.sleep(0.1)

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
    table = table.filter(pl.col("country").is_not_null())
    table = table.unique()

    # Get a list of all the latitude, longitude, and publication date values
    lat_values = table["latitude"].to_list()
    lng_values = table["longitude"].to_list()
    publication_dates = table["published_date"].to_list()

    # Combine the title and description into a single column, providing some styling as well
    table = (
        table
        .with_columns(title_description=pl.concat_str(
            '<div style="font-size: 18px; font-weight: bold; padding-bottom: 4px; text-wrap: balance;">' +
            pl.col("title") +
            "</div>" +
            '<div style="font-size: 14px; font-style: italic; display: table-row; text-wrap: balance;">'+
            pl.col("description") +
            "</div>"
        ))
        .with_columns(city_country=pl.concat_str(
            '<div style="font-size: 14px;">' +
            pl.col("city") + "," +
            "</div>" +
            '<div style="font-size: 14px;">'+
            pl.col("country") +
            "</div>"
        ))
        .with_columns(link=pl.concat_str(
            '<a href="' +
            "http://archive.is/newest/" + pl.col("url") + '" target="_blank" rel="noopener noreferrer">' +
            '<svg aria-hidden="true" role="img" viewBox="0 0 384 512" style="height:1em;width:0.75em;vertical-align:-0.125em;margin-left:auto;margin-right:auto;font-size:inherit;fill:white;overflow:visible;position:relative;"><path d="M320 0c-17.7 0-32 14.3-32 32s14.3 32 32 32l82.7 0L201.4 265.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L448 109.3l0 82.7c0 17.7 14.3 32 32 32s32-14.3 32-32l0-160c0-17.7-14.3-32-32-32L320 0zM80 32C35.8 32 0 67.8 0 112L0 432c0 44.2 35.8 80 80 80l320 0c44.2 0 80-35.8 80-80l0-112c0-17.7-14.3-32-32-32s-32 14.3-32 32l0 112c0 8.8-7.2 16-16 16L80 448c-8.8 0-16-7.2-16-16l0-320c0-8.8 7.2-16 16-16l112 0c17.7 0 32-14.3 32-32s-14.3-32-32-32L80 32z"/></svg>' +
            "</a>"
        ))
        .select(["title_description", "city_country", "link"])
    )

    gt_table = (
        GT(table)
        .fmt_markdown(columns=["title_description", "city_country", "link"])
        .opt_table_font(font=google_font(name="Noto Serif"))
        .cols_width(cases={"city_country": "20%", "link": "35px"})
        .cols_align(align="center", columns="city_country")
        .tab_options(
            table_background_color="#386890",
            table_font_color="white",
            column_labels_hidden=True
        )
    )
    
    # Convert the table to HTML
    table_html = gt_table.as_raw_html()

    # Split the HTML into lines for processing
    lines = table_html.split('\n')

    # Get index of <tr> elements
    tr_indices = [i for i, line in enumerate(lines) if '<tr>' in line]

    # Every row (e.g., <tr>) needs to have a title attribute with the publication date along
    # with latitude and longitude values added as data attributes
    for i in range(len(lat_values)):
        lat = lat_values[i] 
        lng = lng_values[i]
        pdt = publication_dates[i]
        tr_index = tr_indices[i]
        lines[tr_index] = lines[tr_index].replace('<tr>', f'<tr title="{pdt}" data-lat="{lat}" data-lng="{lng}">')

    # Join the lines back into a single HTML string
    table_html = '\n'.join(lines)

    logging.debug("HTML table created")
    return table_html

if __name__ == '__main__':
    logging.info("Starting Flask app")
    app.run(debug=True)