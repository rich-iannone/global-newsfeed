# An LLM-augmented Newsfeed

![View of Application](application_view.png)

This newsfeed application is simple but provides pretty much everything I really need in such an application.
I was inspired by the Nintendo News Channel, which I always though was a fun way to look at world news given
that you have a globe view and the different stories are presented as icons that are interactive (though, I
really like that you could just sit back and watch the globe spin every few seconds, showing you story summaries
very quickly).

![Nintendo News Channel, the inspiration for this](nintendo_news_channel.png)

While this application doesn't have automated tour through the news events of the world, it
at least has a table of news articles. Each row is an article obtained from the New York Times
'Top Stories' API endpoint. On the right side, there *is* a globe with markers showing the
*location* of each news article.

The application does the following things to make this work:

- the articles are fetched as JSON from NYT (mix of different categories, omitting some)
- JSON is parsed and written to CSV with the following fields
    * `"uri"`, `"title"`, `"description"`, `"url"`, `"published_date"`, `"source"`, `"geolocation"`
- the CSV (written with date-time information in its filename) goes through augmentation by sending some of the fields (`"uri"`, `"title"`, `"description"`, `"geolocation"`) to OpenAI for augmentation. In the prompt we ask for:
    * expansion of geolocation to a city and a country, with a best guess of the city if not in the `"geolocation"` field (from inspecting the `"title"`, `"description"`)
    * a return of the data as JSON with the following keys: `"uri"`, `"city"`, `"country"`, `"latitude"`, and `"longitude"`
- upon receiving the response from OpenAI, parse the JSON string into a DataFrame with Polars, and perform a join on the unenriched data with the `"uri"` serving as an ID
- the finished CSV file is read in a later process and a **Great Tables** table is generated
- we add markers to the globe corresponding to lat/lon values add click events to the table so that clicking a row in the table moves to the correct position on the globe
- the table, on the right hand side, has clickable links to take you to the story

It's a great application and the use of the LLM to provide more precise location data (along with coordinates) is very useful. Without the OpenAI integration there would probably be some very error prone parsing of the text to determine location data, involving lookups to obtain the coordinate information (if the location could even be reliably determined).

Here is the prompt used to obtain the location data from ChatGPT:

```
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
dataset (that 'uri' field will serve as an ID for each member).

One last thing, be sure to give me just the JSON string without any conversational text before
and after. I want to be sure I can depend on your output as consistent input for my processing.
```

It does return a response with JSON and it's suitably clean enough to use as input in later
processing steps in the application.
