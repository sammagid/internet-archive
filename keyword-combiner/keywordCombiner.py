import config
import argparse
import os
import re
import json
import requests
import urllib.parse
import pandas as pd
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
import spacy
import yake
from collections import Counter
from openai import OpenAI

# disable parallelism to avoid forking errors
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# import API keys
OPENAI_API_KEY = config.OPENAI_API_KEY

# cookies for authentication
COOKIES = config.COOKIES

# import paths for reading and writing
DATASET_FOLDER = config.DATASET_FOLDER
OUTPUT_FOLDER = config.OUTPUT_FOLDER

# map of MediaCloud collection strings to IDs
REQUEST_COLLECTIONS = {"us": 34412234}

# initializing API clients
openaiClient = OpenAI(api_key = OPENAI_API_KEY)

def fetch_data(collection, date):
    """
    Fetches one day's worth of news data from a MediaCloud collection.

    Args:
        collection (string): A string designator for a MediaCloud collection, e.g.
            "us" for United States – National,
            or anything else listed in REQUEST_COLLECTIONS.
        date (string): Date of news to be fetched, in format "MM-DD-YYYY".

    Returns:
        out_path (string): Path where CSV data exists or was fetched to.
    """
    # format dataset save path
    out_path = os.path.join(DATASET_FOLDER, f"{dataset_name}.csv")

    # check if dataset already fetched
    if os.path.exists(out_path):
        print("MediaCloud data already exists! Nothing to fetch.")
    else:
        print("Fetching data from MediaCloud...")
        # adjust date format for GET request
        date_formatted = date.replace("-","/")
        
        # building URL parameters
        parameters = [{
            "query": "*",
            "startDate": date_formatted,
            "endDate": date_formatted,
            "collections": [REQUEST_COLLECTIONS[collection]],
            "sources": [],
            "platform": "onlinenews-mediacloud"
        }]

        # convert parameters to JSON string then encode
        json_str = json.dumps(parameters)
        json_encoded = urllib.parse.quote(json_str)

        # build full URL, first base then parameters
        request_url = 'https://search.mediacloud.org/api/search/download-all-content-csv?qS='
        request_url += json_encoded

        # perform GET request
        response = requests.get(request_url, cookies=COOKIES)

        # handle bad response
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: {response.status_code} - {response.text}")

        # save dataset
        with open(out_path, "wb") as file:
            file.write(response.content)

    return out_path

def load_data(filepath, language):
    """
    Loads in MediaCloud news dataset, optionally filtering by language.

    Args:
        filepath (string): Path to MediaCloud dataset CSV file.
        language (string): Language to filter by (e.g. "en").
    
    Returns:
        pandas.DataFrame: A table with all the given articles from MediaCloud.
    """
    df = pd.read_csv(filepath)
    if language:
        df = df[df["language"] == language].copy()
    return df

def get_headline_list(data):
    """
    Extracts a list of headlines from a MediaCloud dataframe.

    Args:
        data (pandas.DataFrame): A dataframe of headlines from MediaCloud.
    
    Returns:
        string[]: List of headlines.
    """
    return data["title"].tolist()

def bert_keywords(headlines, dataset_name):
    """
    Runs a BERTopic analysis of a headline list to calculate top headline topics.

    Args:
        headlines (string[]): List of headlines from MediaCloud.
        dataset_name (string): Name of dataset (used for caching path).
    
    Returns:
        string: list of headline topics and frequencies, separated by new lines, e.g.
            World Cup: 435
            New iPhone: 210
            Canadian Elections: 177
    """
    # path to cache string output
    filepath = os.path.join(OUTPUT_FOLDER, dataset_name, "bert-out.txt")

    # check if output has already been calculated/cached, if so load
    if os.path.exists(filepath):
        print("BERTopic keywords already exist! Nothing to run.")
        with open(filepath, 'r') as file:
            out_text = file.read()
    else:
        print("Running BERTopic...")
        # initialize vectorizer model to 3-6 word range
        vectorizer_model = CountVectorizer(ngram_range=(3, 6), stop_words="english")

        # model in BERTopic
        topic_model = BERTopic(vectorizer_model=vectorizer_model)
        topics, _ = topic_model.fit_transform(headlines)
        topic_info = topic_model.get_topic_info()

        # get the top topic for each embedding with frequencies
        topics_list = [f"{row['Representation'][0]}: {row['Count']}" for _, row in topic_info.iloc[1:].iterrows()]

        # format as string and save
        out_text = '\n'.join(topics_list)
        with open(filepath, 'w') as file:
            file.write(out_text)
        
    # return output
    return out_text

def spacy_keywords(headlines, dataset_name):
    """
    Runs a spaCy NER analysis of a headline list to calculate top headline topics.

    Args:
        headlines (string[]): List of headlines from MediaCloud.
        dataset_name (string): Name of dataset (used for caching path).
    
    Returns:
        string: List of headline topics and frequencies, separated by new lines, e.g.
            World Cup: 435
            New iPhone: 210
            Canadian Elections: 177.
    """
    # path to cache string output
    filepath = os.path.join(OUTPUT_FOLDER, dataset_name, "spacy-out.txt")

    # check if output has already been calculated/cached, if so load
    if os.path.exists(filepath):
        print("spaCy keywords already exist! Nothing to run.")
        with open(filepath, 'r') as file:
            out_text = file.read()
    else:
        print("Running spaCy...")
        # set up spaCy
        nlp = spacy.load("en_core_web_md")
        keywords = []

        # run spaCy keyword extraction
        for doc in nlp.pipe(headlines, batch_size=1000):
            keywords.extend([ent.text for ent in doc.ents if ent.label_ in {"PERSON", "ORG", "GPE", "EVENT"}])

        # get top 100
        top_keywords = Counter(keywords).most_common(100)

        # join keywords and frequencies
        keyword_list = [f"{pair[0]}: {pair[1]}" for pair in top_keywords]

        # format and save
        out_text = '\n'.join(keyword_list)
        with open(filepath, 'w') as file:
            file.write(out_text)

    # return output
    return out_text

def yake_keywords(headlines, dataset_name):
    """
    Runs a YAKE keyword extraction on a headline list to calculate top headline topics.

    Args:
        headlines (string[]): List of headlines from MediaCloud.
        dataset_name (string): Name of dataset (used for caching path).
    
    Returns:
        string: list of headline topics and frequencies, separated by new lines, e.g.
            World Cup: 435
            New iPhone: 210
            Canadian Elections: 177
    """
    # path to cache string output
    filepath = os.path.join(OUTPUT_FOLDER, dataset_name, "yake-out.txt")

    # check if output has already been calculated/cached, if so load
    if os.path.exists(filepath):
        print("YAKE keywords already exist! Nothing to run.")
        with open(filepath, 'r') as file:
            out_text = file.read()
    else:
        print("Running YAKE...")
        # extract keywords with YAKE
        kw_extractor = yake.KeywordExtractor(n=5, top=100)
        all_keywords = []
        for title in headlines:
            keywords = kw_extractor.extract_keywords(title)
            all_keywords.extend([kw for kw, score in keywords])
        
        # count 50 most common
        top_keywords = Counter(all_keywords).most_common(100)

        # join keywords and frequencies
        keyword_list = [f"{pair[0]}: {pair[1]}" for pair in top_keywords]

        # format and save
        out_text = '\n'.join(keyword_list)
        with open(filepath, 'w') as file:
            file.write(out_text)

    # return output
    return out_text

def askOpenAI(prompt, model):
    """
    Sends a prompt to the OpenAI client and returns the response.

    Args:
        prompt (string): Prompt for AI to answer.
        model (string): Which OpenAI model to use.
    
    Returns:
        string: Response from AI client.
    """
    print("Summarizing with OpenAI...")
    # create whole message object
    inputMessages = [
        {
            "role": "system",
            "content": """
                       You are an artificial intelligence assistant and you should base your responses
                       off of the data provided to you and what you know about the websites referenced.
                       Do not hallucinate anything. Do not base your answers on news information you
                       have been trained on. Only base your answers on the data provided.
                       """,
        },
        {   
            "role": "user",
            "content": prompt,
        },
    ]

    # prompt response
    response = openaiClient.chat.completions.create(
        model=model,
        messages=inputMessages,
    )

    # return just text content portion
    return response.choices[0].message.content

def create_summarizing_prompt(topics_list):
    """
    Creates a prompt for an LLM chatbot based on a list of topic/frequency lists.

    Args:
        topics_list (string[]): A list of topic/frequency list strings, e.g. those generated by the bert_keywords(), spacy_keywords(), and yake_keywords() functions.

    Returns:
        string: A prompt asking an LLM chatbot to summarize the provided lists of topics.
    """
    # initial prompt
    prompt = "Here are three lists of news topics and their frequencies."
    prompt += "Please summarize them into the top 50 news topics between these lists."
    prompt += "Each topic should be a short, 2-5 word description which could be provided to users as a useful keyword filter."
    prompt += "Each topic should also be an intelligible, specific news topic/event/person, not vague topics like simply 'Bill' or 'Cup'."
    # prompt += "Provide them as a numbered list, don't include their frequency count, and don't include any text before or after the list."
    prompt += "Don't include their frequency count. Provide them as an ordered list in JSON notation."
    prompt += "Don't include any text before or after the JSON list. Your response should be a valid, parseably JSON file."
    prompt += "Additionally, don't include the ```json tag at the beginning or ``` at the end. Those are not parseable."

    # add as many topics lists as provided.
    for i in range(len(topics_list)):
        prompt += f"\nList {i}\n"
        prompt += topics_list[i]

    return prompt

def summarize_topics(topics_list, model = "gpt-4o"):
    """
    Uses an OpenAI model to summarize a list of news topic/frequency lists.

    Args:
        topics_list (string[]): A list of topic/frequency list strings, e.g. those generated by the bert_keywords(), spacy_keywords(), and yake_keywords() functions.
        model (string): Which OpenAI model to use.

    Returns:
        string: a JSON-formatted list of top news topics, as summarized by OpenAI.
    """
    # generate prompt
    prompt = create_summarizing_prompt(topics_list)
    # ask chatbot and return answer
    results = askOpenAI(prompt, model)
    return results

if __name__ == "__main__":
    # parse command line arguments
    parser = argparse.ArgumentParser(description = "Summarize news topics for a given date and MediaCloud collection.")
    parser.add_argument("collection", help = "MediaCloud collection to summarize from (e.g. 'us').")
    parser.add_argument("date", help = "Date to summarize news topics for (format: 'MM-DD-YYYY').")
    args = parser.parse_args()

    # check date format
    if not re.match(r"\d{2}-\d{2}-\d{4}", args.date):
        parser.error("Date must be in MM-DD-YYYY format.")

    # print data and collection information to console
    print(f"\nRetrieving news topics from {args.date} in the '{args.collection}' collection.\n")

    # format dataset name for path and file creation
    dataset_name = f"mediacloud-{args.collection}-{args.date}"

    # make dataset folder if needed
    os.makedirs(DATASET_FOLDER, exist_ok=True)

    # fetch data if it does not already exist and save path
    dataset_path = fetch_data(args.collection, args.date)

    # make a caching folder if needed
    os.makedirs(os.path.join(OUTPUT_FOLDER, dataset_name), exist_ok=True)

    # load data
    data = load_data(dataset_path, "en")

    # get a list of headlines
    headlines = get_headline_list(data)

    # run all three keyword extractions
    keywords_lists = []
    keywords_lists.append(bert_keywords(headlines, dataset_name))
    keywords_lists.append(spacy_keywords(headlines, dataset_name))
    keywords_lists.append(yake_keywords(headlines, dataset_name))

    # summarize prompt with OpenAI client and print answer
    results = create_summarizing_prompt(keywords_lists)
    print("\nResults:")
    print(results)

    # save results to file if non-empty response
    if results is not None:
        with open(os.path.join(OUTPUT_FOLDER, dataset_name, "all-out.json"), "w") as file:
            file.write(results)
    else:
        print("No response from OpenAI client.")