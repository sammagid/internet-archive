# selenium imports
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# local imports
import config

# start Firefox
driver = webdriver.Firefox()

# changing the property of the navigator value for webdriver to undefined 
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

driver.get("https://chatgpt.com")

wait = WebDriverWait(driver, 10)  # Wait up to 10 seconds
textarea = wait.until(EC.visibility_of_element_located((By.ID, "prompt-textarea")))
textarea.click()
textarea.send_keys("Hello")
textarea.send_keys(Keys.RETURN)

input("Press Enter to close the browser...")