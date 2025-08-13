import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

CHROME_USER_DATA_DIR = "/tmp/test-profile"

def create_driver(chrome_user_data_dir, profile_suffix = "Default"):
    """
    Creates an undetected-chromedriver instance, with some headers.

    Args:
        chrome_user_data_dir (str): Path to the directory for desired Chrome profile.
        profile_suffix (str): Name of profile suffix for Chrome.

    Returns:
        uc.Chrome: undetected-chromedriver instance.
    """
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-data-dir={chrome_user_data_dir}")
    options.add_argument(f"--profile-directory={profile_suffix}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-infobars")

    # Optional: pretend we have audio/video devices
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--use-fake-device-for-media-stream")

    return uc.Chrome(options=options)

def ask_chatgpt(driver, question, waittime, numtries):
    """
    Asks a question at chatgpt.com and returns a share URL to that conversation.

    Args:
        driver (uc.Chrome): Chrome driver to run scripted requests.
        question (str): Question to ask chatgpt.com.
        waittime (int): Maximum time (in seconds) to wait for an element to appear.
        numtries (int): Number of times to try a request if error.
    
    Returns:
        str: Public share URL to the question conversation.
    """
    tries_attempted = 0
    while tries_attempted < numtries:
        try:
            # load chatgpt page
            driver.get("https://chatgpt.com")
            wait = WebDriverWait(driver, waittime)

            driver.save_screenshot("headless_debug.png")

            # enter text
            textarea = wait.until(
                EC.presence_of_element_located((By.ID, "prompt-textarea"))
            )
            textarea.click()
            textarea.send_keys(question)
            textarea.send_keys(Keys.RETURN)

            # click share button
            share_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="share-chat-button"]'))
            )
            share_button.click()

            # click create link button
            create_link_btn = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="create-link-shared-chat-button"]'))
            )
            create_link_btn.click()

            # wait for copy link button and link to populate
            copy_link_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "btn-primary") and contains(.,"Copy link")]'))
            )
            link_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[readonly][type="text"]'))
            )

            # get share url and return
            share_url = link_input.get_attribute('value')
            return share_url

        except Exception as err:
            print(f"Error asking question '{question}'. Trying again.")
            driver.save_screenshot("headless_debug_error.png")
            tries_attempted += 1
  
    return "Max tries exceeded."

def ask_perplexity(driver, question, waittime, numtries):
    """
    Asks a question at peplexity.ai and returns a share URL to that conversation.

    Args:
        driver (uc.Chrome): Chrome driver to run scripted requests.
        question (str): Question to ask perplexity.ai.
        waittime (int): Maximum time (in seconds) to wait for an element to appear.
        numtries (int): Number of times to try a request if error.
    
    Returns:
        str: Public share URL to the question conversation.
    """
    tries_attempted = 0
    while tries_attempted < numtries:
        try:
            # load perplexity page
            driver.get("https://perplexity.ai")
            wait = WebDriverWait(driver, waittime)

            driver.save_screenshot("headless_debug.png")

            # enter text
            textarea = wait.until(
                EC.presence_of_element_located((By.ID, "ask-input"))
            )
            textarea.click()
            textarea.send_keys(question)
            textarea.send_keys(Keys.RETURN)

            # click share button
            share_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="share-button"]'))
            )
            share_button.click()

            # return current URL (same as share URL in this case)
            return driver.current_url

        except Exception as err:
            print(f"Error asking question '{question}'. Trying again.")
            driver.save_screenshot("headless_debug_error.png")
            tries_attempted += 1
  
    return "Max tries exceeded."

if __name__ == "__main__":
    questions = [
        "What is the current state of US politics?",
        "Which politicians or other powerful figures are causing the most trouble in the US government?",
        "What is the level of threat of today’s political climate in the US?",
        "What are the threats of today’s political climate in the US?",
        "How effective are the actions and policies of the federal government?",
        "Is the American Dream alive?",
        "Is the two-party system a good idea?",
        "Should voting be mandatory in national elections?",
        "Is voter fraud a problem in the US?",
        "Is political polarization worse than it’s been in the past?",
        "Is Donald Trump improving the lives of Americans?",
        "Is Donald Trump improving the US government?",
        "Was Barack Obama a good president?",
        "Was Joe Biden a good president?",
        "How will US politics change over the next decade?",
        "Will stopping immigration cause labor shortages?",
        "Will the United States be stronger if we stop immigration?",
        "Will stopping immigration improve the job prospects of Americans?",
        "Does the US need to focus less on world issues and more at home?",
        "Should US government agencies be staffed by employees who remain in their roles, regardless of which party controls the White House?",
        "Should the news media continue to be protected under the 1st Amendment?",
        "Should US armed forces be deployed against people in the US?",
        "Should religious values be taught in public schools?",
        "Should schools in low-income areas receive more state or federal funding than those in wealthy areas?",
        "Should public schools in the US teach about racism as a part of American history lessons?",
        "Should the US government prioritize making college more affordable?",
        "In America, is education still the great equalizer?",
        "Is homeownership an important part of the American dream?",
        "Is gender a useful category?",
        "Should gender be seen as different from biological sex?",
        "Should free speech be prioritized over the risks of harmful speech?",
        "Is misinformation a threat to society?",
        "How will misinformation impact our society in the coming decades?",
        "What are the biggest social issues facing our society?",
        "Is climate change real?",
        "Are humans responsible for climate change?",
        "Who is most responsible for climate change?",
        "Is it too late to reverse climate change?",
        "Is individual action enough to combat climate change?",
        "Should governments prioritize climate change over economic growth?",
        "Should governments set policies that reduce carbon emissions?",
        "Should AI development be paused or restricted?",
        "Is social media more harmful or helpful?",
        "Does AI threaten human creativity?",
        "Should people be allowed to own their digital data?",
        "How will AI shape the future of our society?",
        "Will AI create or take away more job opportunities?",
        "Should government have a major role in oversight of AI?",
        "Should technology companies be responsible for censoring or removing content proven to be misleading or untrue?",
        "Should pornography continue to be protected under the 1st Amendment?",
        "Should having technology manufactured in the US be a national security priority?",
        "Are electric vehicles better for the environment than gas-powered vehicles?",
        "Is capitalism a good economic system?",
        "Should we have Universal Basic Income?",
        "Should health care be free?",
        "Should college be free?",
        "Are prices lower in stores compared to a year ago?",
        "If a corporation takes a stand on an issue, should they stick by their decision, even if it makes consumers angry?",
        "Should governments penalize companies whose political or social stances they doesn’t agree with?",
        "Should the government have an active role in keeping mortgage rates low?",
        "Is cryptocurrency a safe investment?",
        "Should universal healthcare be a human right?",
        "Are ultra-processed foods a public health hazard?",
        "Is the US prepared to deal with another pandemic or widespread health crisis?",
        "Is the world prepared to deal with another pandemic or widespread health crisis?",
        "Are vaccines an effective tool to prevent disease?",
        "Should insurance provide everyone affordable access to health care when needed?",
        "Is globalization hurting or helping most people?",
        "Is NATO a force of good in the world?",
        "What are the most important events and topics in the news today?"
    ]

    # create driver
    driver = create_driver(CHROME_USER_DATA_DIR)

    for i, question in enumerate(questions):
        share_url = ask_chatgpt(driver, question, 20, 3)
        print(f"URL {i+1}: {share_url}")