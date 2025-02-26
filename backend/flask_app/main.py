"""
A simple web scraper that scrapes a URL and returns the keywords and their associated information.
"""

from http import HTTPStatus
from flask import Flask, render_template, request
from flask_cors import CORS
from backend.helpers.functions import relevant_information, scrape_url

app = Flask(__name__)
CORS(app)


@app.post("/web_scraper/")
def index():
    """
    This function handles the web scraper.
    """
    if request.method == "POST":
        url = request.form["url"]
        try:
            return {"content": relevant_information(scrape_url(url)), "status": HTTPStatus.OK}
        # General exception handling
        except Exception as e:
            return {"content": f"Error during web scraping: {e}", "status": HTTPStatus.INTERNAL_SERVER_ERROR}
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
