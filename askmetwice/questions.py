import ast
import os
import json
from datetime import datetime

import pandas as pd
from tqdm import tqdm

import chatbots as cb

def generate_questions(headline, use_ai_questions):
    """
    Generates a list of questions to ask about a news headline. If use_ai_questions is true, the
    function will use an AI client (currently gpt-4o) to generate questions. Otherwise, a basic,
    non-generated question will be used (right now "Tell me about this headline").
    
    Args:
        headline (str): Any news headline.
        use_AI_questions (boolean): Whether to include AI-generated questions in the question set.
    
    Returns:
        str[]: A list of questions to ask about the input headline.
    """
    # initialize empty list to populate
    question_list = []

    # add basic question
    basic_question = "Tell me about this headline:"
    question_list.append(f"{basic_question} {headline}")

    # add ai generated questions if specified
    if use_ai_questions:
        # build question-getting prompt for chatbot
        prompt = "Come up with a list of 5-10 questions people might ask about this headline. "
        prompt += "Make sure to generate some factual questions, some subjective, and some speculative. "
        prompt += "Each of the questions should include all necessary information so that no additional context is needed to understand what events, people, or topics the question is referring to. "
        prompt += "Provide them as a valid Python list of strings, with no extra text or ``` formatting headers/footers."
        prompt += "\n\n"
        prompt += f"Headline: {headline}"

        # query AI chatbot for a list of natural questions
        response = cb.ask_openai(prompt)

        # get just message out of response
        message = response['response']['choices'][0]['message']['content']

        # just in case, remove headers from message if exist
        message = message.replace("```python", "")
        message = message.replace("```", "")

        # evaluate as a python list and add to question_list
        list_representation = ast.literal_eval(message)
        question_list += list_representation

    return question_list

def add_questions(df, use_ai_questions):
    """
    Adds a set of questions for each headline in a dataset. If use_ai_questions is true, AI
    generated questions will be included. Otherwise, a basic, non-generated question will be used
    (right now "Tell me about this headline").

    Args:
        df (pandas.DataFrame): Dataset of news headlines, with headlines under 'title' column.
        use_ai_questions (boolean): Whether to include AI-generated questions in the question set.

    Returns:
        pandas.DataFrame: A new dataframe with each row holding a different question-headline pair.
    """
    print("Generating questions about headlines.")

    # initialize empty list of rows to hold result
    result_rows = []
    
    # iterate through each title (with progress bar) and generate questions
    for i, row in tqdm(df.iterrows(), total = len(df), desc = "headlines"):
        title = df.at[i, "title"]
        questions = generate_questions(title, use_ai_questions)
        # add a new row to resulting dataframe for each question
        for question in questions:
            row_dict = row.to_dict()
            row_dict['question'] = question
            result_rows.append(row_dict)
    
    # convert rows to dataframe and return
    return pd.DataFrame(result_rows)

def ask_questions(df, chatbots, save_folder):
    """
    Asks a set of questions in a dataframe to a series of chatbots, saves their answers as
    JSON files, and returns a dataframe containing all previous data and the filepaths.

    Args:
        df (pandas.DataFrame): A dataframe of questions to ask (in column 'question') along
        with any other data to be passed through.
        chatbots (str[]): List of chatbot names to query (corresponding to a chatbot name in
        cb_functions).
        save_folder (str): Path to folder to save JSON responses.
    
    Returns:
        pandas.DataFrame: A new dataframe with questions answered in saved JSON files linked
        in 'response path' column.
    """
    print(f"Answering questions about headlines (clients: {chatbots}).")

    # map of ai chatbot names to their function calls
    cb_functions = {
        "perplexity": cb.ask_perplexity,
        "openai": cb.ask_openai,
        "gemini": cb.ask_gemini
    }

    # make sure all chatbots specified are listed in cb_functions
    for chatbot in chatbots:
        if not chatbot in cb_functions.keys():
            raise ValueError("Invalid chatbot specified in ask_questions().")

    # make file path, but make name different if already exists to avoid overwrite
    while os.path.exists(save_folder):
        save_folder += "-new"
    os.makedirs(save_folder, exist_ok=True)

    # start a counter to make simple file names (AMT-2025-07-30-00000.json, etc.)
    counter = 0

    # initialize result as empty list of rows
    result_rows = []

    # iterate through each question (with progress bar) and answer questions
    for i, row in tqdm(df.iterrows(), total = len(df), desc = "questions"):
        for chatbot in chatbots:
            ask_chatbot_function = cb_functions[chatbot]
            # OPTION: use dummy function for testing to speed up significantly
            # def ask_chatbot_function(question):
            #     return {"question": question, "testing": True, "model": "testing"}
            question = df.at[i, "question"]
            # ask chatbot question and save response as JSON
            response = ask_chatbot_function(question)
            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d")
            out_path = os.path.join(save_folder, f"AMT-{timestamp}-{counter:05d}.json")
            with open(out_path, "w") as file:
                json.dump(response, file)
            # record path in resulting dataframe
            row_dict = row.to_dict()
            row_dict['ai client'] = response['model']
            row_dict['response path'] = out_path
            result_rows.append(row_dict)
            # increment counter
            counter += 1
    
    # convert rows to dataframe and return
    return pd.DataFrame(result_rows)