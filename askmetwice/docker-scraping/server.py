from flask import Flask
from scraper import Scraper

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/scrape")
def scrape():
    scrape_chatgpt()

@app.route("/scrape/chatgpt")
def scrape_chatgpt():
    scraper = Scraper()
    response = scraper.ask_chatgpt("What is the capital of France?")
    return format_response(response, "chatgpt")

@app.route("/scrape/perplexity")
def scrape_perplexity():
    scraper = Scraper()
    response = scraper.ask_perplexity("What is the capital of France?")
    return format_response(response, "perplexity")

@app.route("/scrape/grok")
def scrape_grok():
    scraper = Scraper()
    response = scraper.ask_grok("What is the capital of France?")
    return format_response(response, "grok")

def format_response(response, source):
    return {
        "response": "<p>" + response + "</p>",
        "source": source
    }


app.run(host="0.0.0.0", port=5010, debug=True)
