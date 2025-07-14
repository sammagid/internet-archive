"""
Top News Topics AI Retriever

Asks a series of AI chatbots to report the top news topics, and save their responses.

Includes optional arguments --region (news region) and --n (number of topics to requests).

Example Usage: python topTopics.py --region 'us' --n 10

Author: Sam Magid
"""

import config
import argparse
from datetime import datetime
import os
import sys
import feedparser
import pandas as pd
from openai import OpenAI

# api keys
PERPLEXITY_API_KEY = config.PERPLEXITY_API_KEY

# loads ai clients
PERPLEXITY_CLIENT = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")

# folder to output data
OUTPUT_FOLDER = "outputs"

# dictionary of region strings for prompts
REGION_STRINGS = {'us': " from the US",
                  'fr': " from France",
                  'in': " from India"}

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

def get_perplexity_responses(prompt):
    """
    Prompts Perplexity AI client to report the top news topics and returns
    resulting data as a dictionary row.

    Args:
        prompt (str): Prompt to ask to generate news topics.

    Returns:
        dict: A dictionary representing the chatbot input/output with the following keys:
            - 'client' (str): Name of the AI client (e.g. 'Perplexity').
            - 'prompt' (str): Prompt asked of the AI client.
            - 'response' (str): Response from the client.
            – 'citations' (str[]): List of URL citations from client.
    """
    print("\nAsking Perplexity for news topics...")

    # ask perplexity the prompt and filter out parts
    response = ask_perplexity(prompt)
    message = response['choices'][0]['message']['content']
    citations = response['citations']

    # return dictionary row with data
    return {'client': 'Perplexity', 'prompt': prompt, 'response': message, 'citations': citations}

def main():
    """
    Parses command line arguments, prompts AI clients, and saves responses to CSV file.
    """
    # parse command line arguments
    parser = argparse.ArgumentParser(description = "Asks AI clients to give top news topics.")
    parser.add_argument("--region", default = "", help = "Region to ask AI clients about in ISO 3166-1 alpha-2 country codes (e.g. 'us', 'fr', 'in').")
    parser.add_argument("--n", default = None, help = "Number of topics to ask for.")
    args = parser.parse_args()
    
    # create output directory if not exist
    todays_date = datetime.today().strftime("%m-%d-%Y")
    out_dir = os.path.join(OUTPUT_FOLDER, todays_date)
    os.makedirs(out_dir, exist_ok=True)

    # get optional region string from REGION_STRINGS dictionary
    try:
        region_string = REGION_STRINGS[args.region] if args.region else ""
    except KeyError:
        # handle missing region
        print(f"Error: Unknown region '{args.region}'. Currently supported regions: {", ".join(REGION_STRINGS.keys())}.")
        sys.exit(1)

    # print useful information to terminal
    print(f"\nAsking AI chatbots for{f" {args.n}" if args.n else ""} top news topics{region_string} on {todays_date}.")

    # build prompt with optional arguments
    prompt = f"What are the top{f" {args.n}" if args.n else ""} news topics{region_string} today?"

    # create empty list of rows, to be filled by AI client response data
    rows = []

    # populate AI client response data
    rows.append(get_perplexity_responses(prompt))

    # create dataframe
    df = pd.DataFrame(rows)

    # save to CSV file
    out_file = os.path.join(out_dir, f"{todays_date}{f"_{args.region}" if args.region else ""}{f"_{args.n}" if args.n else ""}.csv")
    df.to_csv(out_file, index=False)

    # print success statement
    print(f"\nAI client responses saved to {out_file}.\n")

if __name__ == "__main__":
    main()