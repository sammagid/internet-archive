import argparse
from datetime import datetime
import os
import feedparser
import pandas as pd

BASE_FEED_URL = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
OUTPUT_FOLDER = "outputs"

def fetch_articles(host_lang, geo_loc, client_ed_id):
    """
    Fetches the "Top Stories" from the Google News RSS feed.

    Args:
        host_lang (str): Language of Google News interface (e.g. en-US, en-GB, fr-FR)
        geo_loc (str): Country location variable determining which sources to prioritize (e.g. US, FR, IN)
        client_ed_id (str): News edition designator, determines content of articles (e.g. US:en, IN:hi, IN:en)
    
    Returns:
        pandas.DataFrame: Dataset of article titles and corresponding Google News links
    """
    # build feed request URL
    feed_url = f"{BASE_FEED_URL}?hl={host_lang}&gl={geo_loc}&ceid={client_ed_id}"

    # retrieve rss feed with feedparser
    rss_feed = feedparser.parse(feed_url)

    # populate a list of rows
    rows = []
    for entry in rss_feed.entries:
        rows.append({'title': entry.title, 'url': entry.link})

    # turn into pandas dataframe and return
    df = pd.DataFrame(rows)
    return df

def main():
    """
    Parses command line arguments, fetches RSS data, and saves to appropriate location (making directories if needed).
    """
    # parse command line arguments
    parser = argparse.ArgumentParser(description = "Retrieve and save top stories from Google News RSS feed.")
    parser.add_argument("host_lang", help = "Language of Google News interface (e.g. en-US, en-GB, fr-FR)")
    parser.add_argument("geo_loc", help = "Country location variable determining which sources to prioritize (e.g. US, FR, IN)")
    parser.add_argument("client_ed_id", help = "News edition designator, determines content of articles (e.g. US:en, IN:hi, IN:en)")
    args = parser.parse_args()
    
    # create output directory if not exist
    todays_date = datetime.today().strftime("%m-%d-%Y")
    out_dir = os.path.join(OUTPUT_FOLDER, todays_date)
    os.makedirs(out_dir, exist_ok=True)

    # fetch articles and save to csv
    df = fetch_articles(host_lang = args.host_lang, geo_loc = args.geo_loc, client_ed_id = args.client_ed_id)
    out_file = os.path.join(out_dir, f"{args.host_lang}_{args.geo_loc}_{args.client_ed_id}.csv")
    df.to_csv(out_file, index=False)

if __name__ == "__main__":
    main()