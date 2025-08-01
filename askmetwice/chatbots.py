# This script will change when we gain better access to chatbot backends or webscraping capability.

from datetime import datetime

from openai import OpenAI
from google import genai
from google.genai import types

import config

# api keys
PERPLEXITY_API_KEY = config.PERPLEXITY_API_KEY
OPENAI_API_KEY = config.OPENAI_API_KEY
GEMINI_API_KEY = config.GEMINI_API_KEY

# loads ai clients
PERPLEXITY_CLIENT = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")
OPENAI_CLIENT = OpenAI(api_key = OPENAI_API_KEY)
GEMINI_CLIENT = genai.Client(api_key = GEMINI_API_KEY)

def ask_perplexity(prompt, model = "sonar-pro"):
    """
    Asks a question of the Perplexity AI API client and returns the response.

    Args:
        prompt (str): Prompt to send to Perplexity client.
        model (str): Which Perplexity LLM model to use.
    
    Returns:
        dict: Dictionary representation of response from Perplexity, along with metadata.
    """
    # build the message (can also include a system prompt)
    messages = [{"role": "user", "content": prompt}]

    # send prompt to client and return response message
    response = PERPLEXITY_CLIENT.chat.completions.create(
        model = model,
        messages = messages,
    ).model_dump()
    
    # build dictionary result and return it
    result = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'model': f"Perplexity {model}",
        'prompt': prompt,
        'response': response
    }
    return result

def ask_openai(prompt, model = "gpt-4o"):
    """
    Asks a question of the OpenAI API client and returns the response.

    Args:
        prompt (string): Prompt for OpenAI client to answer.
        model (string): Which OpenAI model to use.
    
    Returns:
        dict: Dictionary representation of response from OpenAI, along with metadata.
    """
    # build the message (can also include a system prompt)
    messages = [{"role": "user", "content": prompt}]

    # send prompt to client and return response message
    response = OPENAI_CLIENT.chat.completions.create(
        model=model,
        messages=messages,
    ).model_dump()

    # build dictionary result and return it
    result = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'model': f"OpenAI {model}",
        'prompt': prompt,
        'response': response
    }
    return result

def ask_gemini(prompt, model = "gemini-2.5-flash"):
    """
    Asks a question of the Google Gemini API client and returns the response.

    Args:
        prompt (string): Prompt for Gemini client to answer.
        model (string): Which Gemini model to use.
    
    Returns:
        dict: Dictionary representation of response from Gemini, along with metadata.
    """
    # configure search tool
    grounding_tool = types.Tool(
        google_search=types.GoogleSearch()
    )

    # configure settings
    config = types.GenerateContentConfig(
        tools=[grounding_tool]
    )

    # query client and save response
    response = GEMINI_CLIENT.models.generate_content(
        model = model,
        contents = prompt,
        config = config
    ).model_dump()

    # build dictionary result and return it
    result = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'model': f"Google {model}",
        'prompt': prompt,
        'response': response
    }
    return result

# map of ai chatbot names to their function calls
CB_FUNCTIONS = {
    "perplexity": ask_perplexity,
    "openai": ask_openai,
    "gemini": ask_gemini
}