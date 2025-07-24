# selenium imports
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# local imports
import config

# proxy details
proxy_host = config.PROXY_HOST
proxy_port = config.PROXY_PORT
proxy_user = config.PROXY_USER
proxy_pass = config.PROXY_PASS

# set up Firefox options
options = Options()
options.set_preference("network.proxy.type", 1)
options.set_preference("network.proxy.socks", proxy_host)
options.set_preference("network.proxy.socks_port", proxy_port)
options.set_preference("network.proxy.socks_version", 5)
options.set_preference("network.proxy.socks_username", proxy_user)
options.set_preference("network.proxy.socks_password", proxy_pass)
options.set_preference("signon.autologin.proxy", True)

# start Firefox
driver = webdriver.Firefox(options=options)

# changing the property of the navigator value for webdriver to undefined 
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

driver.get("https://chatgpt.com")

wait = WebDriverWait(driver, 10)  # Wait up to 10 seconds
textarea = wait.until(EC.visibility_of_element_located((By.ID, "prompt-textarea")))
textarea.click()
textarea.send_keys("Hello")
textarea.send_keys(Keys.RETURN)

input("Press Enter to close the browser...")