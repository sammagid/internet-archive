import feedparser
import pandas as pd

# base url of google news rss feed
BASE_FEED_URL = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

def split_titles(df):
    """
    Splits a Google News headline ("[title] - [news outlet]") into separate columns.

    Args:
        df (pandas.DataFrame): Dataset of news headlines, with headlines under 'title' column
        and empty 'news-outlet' column.

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

def fetch_articles(host_lang, geo_loc, client_ed_id, separate_titles = True, article_limit = 0):
    """
    Fetches the "Top Stories" from the Google News RSS feed.

    Args:
        host_lang (str): Language of Google News interface (e.g. en-US, en-GB, fr-FR)
        geo_loc (str): Country location variable determining which sources to prioritize (e.g. US, FR, IN)
        client_ed_id (str): News edition designator, determines content of articles (e.g. US:en, IN:hi, IN:en)
        separate_titles (bool): Whether to separate news outlet information from headline title.
        article_limit (int): Max number of articles to fetch.
    
    Returns:
        pandas.DataFrame: Dataset of article titles and other metadata.
    """
    print("Fetching today's articles from Google News...")

    # build feed request URL
    feed_url = f"{BASE_FEED_URL}?hl={host_lang}&gl={geo_loc}&ceid={client_ed_id}"

    # retrieve rss feed with feedparser
    rss_feed = feedparser.parse(feed_url)

    # populate a list of rows
    rows = []
    for entry in rss_feed.entries:
        rows.append({"source": "Google News", "title": entry.title, "url": entry.link})

    # turn into pandas dataframe and limit if set
    if article_limit: # if limit set, cut off extra articles
        df = pd.DataFrame(rows[:article_limit])
    else:
        df = pd.DataFrame(rows)
    print(f"Successfully fetched {len(df)} articles!")

    # separate titles from news outlet, if specified
    if separate_titles:
        df.insert(2, 'news-outlet', None)
        split_titles(df)
    
    return df