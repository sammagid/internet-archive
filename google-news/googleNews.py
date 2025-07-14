"""
Google News AI Chatbot Reponses

Retrieves the top stories from Google News RSS feed and asks AI chatbots to provide
information about them.

Example Usage: python googleNews.py 'en-US' 'US' 'US:en'

Author: Sam Magid
"""

import config
import argparse
from datetime import datetime
import os
import feedparser
import pandas as pd
from tqdm import tqdm
from openai import OpenAI

# base url of google news rss feed
BASE_FEED_URL = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

# api keys
PERPLEXITY_API_KEY = config.PERPLEXITY_API_KEY

# loads ai clients
PERPLEXITY_CLIENT = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")

# folder to output data
OUTPUT_FOLDER = "outputs"

def fetch_articles(host_lang, geo_loc, client_ed_id, split_titles):
    """
    Fetches the "Top Stories" from the Google News RSS feed.

    Args:
        host_lang (str): Language of Google News interface (e.g. en-US, en-GB, fr-FR)
        geo_loc (str): Country location variable determining which sources to prioritize (e.g. US, FR, IN)
        client_ed_id (str): News edition designator, determines content of articles (e.g. US:en, IN:hi, IN:en)
        split_titles (bool): Whether to leave room for news outlets, if splitting titles.
    
    Returns:
        pandas.DataFrame: Dataset of article titles and corresponding Google News links
    """
    print("\nFetching today's articles from Google News...")

    # build feed request URL
    feed_url = f"{BASE_FEED_URL}?hl={host_lang}&gl={geo_loc}&ceid={client_ed_id}"

    # retrieve rss feed with feedparser
    rss_feed = feedparser.parse(feed_url)

    # populate a list of rows
    rows = []
    for entry in rss_feed.entries:
        if split_titles: # leave room for news-outlet split
            rows.append({"source": "Google News", "title": entry.title, "news-outlet": "", "url": entry.link})
        else:
            rows.append({"source": "Google News", "title": entry.title, "url": entry.link})

    # turn into pandas dataframe and return
    df = pd.DataFrame(rows)
    print(f"Successfully fetched {len(df)} articles!")
    return df

def split_titles(df):
    """
    Splits a Google News headline ("[title] - [news outlet]") into separate columns.

    Args:
        df (pandas.DataFrame): Dataset of news headlines, with headlines under 'title' column.

    Returns:
        None (modifies data in place).
    """
    # exceptions with one hyphen in news outlet name
    one_hyphen_exceptions = ["ABC News - Breaking News, Latest News and Videos"]

    # helper function to split titles
    def split_single_title(title):
        # split title into parts by hyphen
        parts = title.split(" - ")
        # handle different number of hyphen cases
        if len(parts) == 2:
            # normal case: one hyphen, split into title and outlet
            return pd.Series(parts)
        elif len(parts) > 2:
            # multiple hyphens
            last_two = " - ".join(parts[-2:])
            if last_two in one_hyphen_exceptions:
                # outlet is last two parts joined
                title_part = " - ".join(parts[:-2])
                return pd.Series([title_part, last_two])
            else:
                # outlet is last part only
                title_part = " - ".join(parts[:-1])
                return pd.Series([title_part, parts[-1]])
        else:
            # no hyphen found, no outlet
            return pd.Series([title, ""])

    df[['title', 'news-outlet']] = df['title'].apply(split_single_title)

def ask_perplexity(prompt, model = "sonar-pro"):
    """
    Asks a question of the Perplexity AI API client.

    Args:
        prompt (str): Prompt to send to Perplexity client.
        model (str): Which Perplexity LLM model to use.
    
    Returns:
        dict: Dictionary representation of response from Perplexity, including message and citations.
    """
    # build the message (can also include a system prompt)
    messages = [{"role": "user", "content": prompt}]

    # send prompt to client and return response message
    response = PERPLEXITY_CLIENT.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.model_dump()

def add_perplexity_responses(df):
    """
    Prompts Perplexity AI client to respond to news titles from a dataset and populates
    that dataset with Perplexity's answers and citations.

    Args:
        df (pandas.DataFrame): Dataset of news headlines, with headlines under 'title' column.

    Returns:
        None (modifies data in place).
    """
    print("\nAsking Perplexity about headlines...")

    # initialize empty columns
    df["perplexity_prompt"] = None
    df["perplexity_response"] = None
    df["perplexity_citations"] = None

    # iterate through each title (with progress bar) and ask Perplexity about it
    for i, row in tqdm(df.iterrows(), total=len(df)):
        # get response from perplexity
        title = df.at[i, "title"]
        prompt = f"Tell me about this headline: {title}"
        response = ask_perplexity(prompt)

        # populate prompt, answer, and citation in dataset
        df.at[i, "perplexity_prompt"] = prompt
        df.at[i, "perplexity_response"] = response['choices'][0]['message']['content']
        df.at[i, "perplexity_citations"] = response['citations']

def main():
    """
    Parses command line arguments, fetches RSS data, prompts AI clients, and saves to appropriate location
    (making directories if needed).
    """
    # parse command line arguments
    parser = argparse.ArgumentParser(description = "Retrieve top stories from Google News RSS feed and ask AI clients about them.")
    parser.add_argument("host_lang", help = "Language of Google News interface (e.g. en-US, en-GB, fr-FR).")
    parser.add_argument("geo_loc", help = "Country location variable determining which sources to prioritize (e.g. US, FR, IN).")
    parser.add_argument("client_ed_id", help = "News edition designator, determines content of articles (e.g. US:en, IN:hi, IN:en).")
    parser.add_argument("--split_titles", action = "store_true", help = "Split titles between title and news outlet component, to discourage AI client from looking directly at headline source.")
    args = parser.parse_args()
    
    # create output directory if not exist
    todays_date = datetime.today().strftime("%m-%d-%Y")
    out_dir = os.path.join(OUTPUT_FOLDER, todays_date)
    os.makedirs(out_dir, exist_ok=True)

    # print useful information to terminal
    print(f"\nAsking AI chatbots about top Google News headlines from {todays_date}.")

    # fetch articles and save to a dataframe
    df = fetch_articles(host_lang = args.host_lang,
                        geo_loc = args.geo_loc,
                        client_ed_id = args.client_ed_id,
                        split_titles = args.split_titles)

    # OPTIONAL (TESTING): separate news outlet from headline
    if args.split_titles:
        split_titles(df)

    # ask perplexity about each headline
    add_perplexity_responses(df)

    # build out file
    out_file = f"{todays_date}_{args.host_lang}_{args.geo_loc}_{args.client_ed_id.replace(":","-")}"
    out_file += "_split" if args.split_titles else ""
    out_file += ".csv"
    out_path = os.path.join(out_dir, out_file)
    df.to_csv(out_path, index=False)

    # print success statement
    print(f"Articles and responses successfully saved to {out_path}.\n")

if __name__ == "__main__":
    main()