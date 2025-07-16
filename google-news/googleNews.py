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
import ast
import json
import feedparser
import pandas as pd
from tqdm import tqdm
from openai import OpenAI

# base url of google news rss feed
BASE_FEED_URL = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

# LIMIT ARTICLES to limit API costs right now
ARTICLE_LIMIT = 5

# api keys
PERPLEXITY_API_KEY = config.PERPLEXITY_API_KEY
OPENAI_API_KEY = config.OPENAI_API_KEY

# loads ai clients
PERPLEXITY_CLIENT = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")
OPENAI_CLIENT = OpenAI(api_key = OPENAI_API_KEY)

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
    if ARTICLE_LIMIT: # if limit set, cut off extra articles
        df = pd.DataFrame(rows[:ARTICLE_LIMIT])
    else:
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

def ask_openai(prompt, model = "gpt-4o"):
    """
    Sends a prompt to the OpenAI client and returns the response.

    Args:
        prompt (string): Prompt for OpenAI client to answer.
        model (string): Which OpenAI model to use.
    
    Returns:
        dict: Dictionary representation of response from OpenAI.
    """
    # build the message (can also include a system prompt)
    messages = [{"role": "user", "content": prompt}]

    # send prompt to client and return response message
    response = OPENAI_CLIENT.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.model_dump()

# map of client names to function calls
CLIENT_FUNCTION_MAP = {
    "perplexity": ask_perplexity,
    "openai": ask_openai
}

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

def generate_questions(headline):
    """
    Generates a list of context-rich questions to ask about a news headline, using
    an AI client (currently gpt-4o).
    
    Args:
        headline (str): Any news headline.
    
    Returns:
        str[]: A list of questions to ask about the input headline.
    """
    # initialize empty list to populate
    question_list = []

    # add basic question
    basic_question = "Tell me about this headline:"
    question_list.append(f"{basic_question} {headline}")

    # build question-getting prompt for chatbot
    prompt = "Come up with a list of questions to ask about this headline. "
    prompt += "Each of the questions should include all necessary context. "
    prompt += "Provide them as a valid Python list of strings, with no extra text or ``` formatting headers/footers."
    prompt += "\n\n"
    prompt += headline

    # query AI chatbot for a list of natural questions
    response = ask_openai(prompt)

    # get just message out of response
    message = response['choices'][0]['message']['content']

    # just in case, remove headers from message if exist
    message = message.replace("```python", "")
    message = message.replace("```", "")

    # evaluate as a python list and add to question_list
    list_representation = ast.literal_eval(message)
    question_list += list_representation

    return question_list

def add_questions(df):
    """
    Prompts an AI client to generate questions for each headline in a dataset.

    Args:
        df (pandas.DataFrame): Dataset of news headlines, with headlines under 'title' column.

    Returns:
        None (modifies data in place).
    """
    print("\nGenerating questions about headlines...")

    # initialize empty question column
    df["questions"] = None
    
    # iterate through each title (with progress bar) and generate questions.
    for i, row in tqdm(df.iterrows(), total=len(df)):
        title = df.at[i, "title"]
        df.at[i, "questions"] = generate_questions(title)

def generate_answers(questions, client):
    """
    Prompts an AI client to answer questions for a set of headline questions.

    Args:
        questions (str[]): A list of questions generated for a given headline.
        client (str): Name of AI client to ask for answers (currently 'perplexity' or 'openai').
    
    Returns:
        dict[]: A list of dictionaries with the following keys:
              - 'question': The question asked of the AI client.
              - 'answer': The response received from the client.
              - 'citations': Any citations received.
    """
    # get function call for client
    ask_client = CLIENT_FUNCTION_MAP[client]

    # initialize empty list of question/answer/citations dicts
    responses = []

    # ask about each question
    for question in questions:
        # ask AI client (currently perplexity)
        response = ask_client(question)

        # separate fields
        answer = response['choices'][0]['message']['content']
        citations = response['citations']

        # add response dict to list of responses
        responses.append({'question': question, 'answer-client': client, 'answer': answer, 'citations': citations})

    # return populated list of questions/responses/citation dicts
    return responses

def add_answers(df, client):
    """
    Prompts an AI client to answer questions for each set of headline questions,
    and populated dataset with those answers.

    Args:
        df (pandas.DataFrame): Dataset of news headlines, with questions under 'questions' column.

    Returns:
        None (modifies data in place).
    """
    print("\nGenerating answers to questions...")

    # initialize empty answers column
    df["question-answers"] = None

    # iterate through each title (with progress bar) and generate answers.
    for i, row in tqdm(df.iterrows(), total=len(df)):
        questions = df.at[i, "questions"]
        df.at[i, "question-answers"] = generate_answers(questions, client)

def jsonify_data(df):
    """
    Turns a populated headline/question/answer/citation dataset into a nicely formatted
    JSON string.

    Args:
        df (pandas.DataFrame): Dataset with at least the following columns:
                             - 'title' (str): Title of news article.
                             - 'news-outlet' (str): News source of article.
                             – 'url' (str): URL pointing to article.
                             - 'question-answers' (dict): A dictionary of all the question/client/answer/citation pairs.

    Returns:
        str: A nicely formatted JSON string of the dataset.
    """
    # build a list of all the data, to be JSONified
    data = []

    # iterate through each row/headline
    for i, row in tqdm(df.iterrows(), total=len(df)):
        headline = df.at[i, "title"]
        source = df.at[i, "source"]
        outlet = df.at[i, "news-outlet"]
        url = df.at[i, "url"]
        qas = df.at[i, "question-answers"]
        data.append({"headline": headline,
                     "source": source,
                     "news-outlet": outlet,
                     "url": url,
                     "questions": qas})
    
    # turn list into a json string and return
    return json.dumps(data, indent=4)

def jsonify_columns(df):
    """
    Converts 'questions' and 'question-answers' columns of df to JSON (to be done before saving).

    Args:
        df (pandas.DataFrame): Dataset of news headlines, with columns:
                             - 'questions' (str[])
                             - 'question-answers' (dict[])
    
    Returns:
        None (modifies data in place).
    """
    df['questions'] = df['questions'].apply(json.dumps)
    df['question-answers'] = df['question-answers'].apply(json.dumps)

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
    # add_perplexity_responses(df)

    # generate questions for each headline and add as column
    add_questions(df)

    # generate answers for each set of questions and add as column
    add_answers(df, "perplexity")

    # create out file name
    out_file = f"{todays_date}_{args.host_lang}_{args.geo_loc}_{args.client_ed_id.replace(":","-")}"
    out_file += "_split" if args.split_titles else ""

    # create full json out file name and save json data
    out_file_json = out_file + ".json"
    out_path_json = os.path.join(out_dir, out_file_json)
    json_data = jsonify_data(df)
    with open(out_path_json, "w") as file:
        file.write(json_data)

    # print success statement
    print(f"\nJSON data successfully saved to {out_path_json}.")

    # jsonify cell output for csv data
    jsonify_columns(df)

    # create full csv out file name and save to csv
    out_file_csv = out_file + ".csv"
    out_path_csv = os.path.join(out_dir, out_file_csv)
    df.to_csv(out_path_csv, index=False)

    # print success statement
    print(f"\nCSV data successfully saved to {out_path_csv}.\n")

if __name__ == "__main__":
    main()