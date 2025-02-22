"""
A simple web scraper that scrapes a URL and returns the keywords and their associated information.
"""

from flask import Flask, render_template, request

from helpers.functions import identify_keywords, scrape_url

app = Flask(__name__)


@app.route("/web_scraper/", methods=["GET", "POST"])
def index():
    """
    This function handles the web scraper.
    """
    if request.method == "POST":
        url = request.form["url"]
        try:
            return identify_keywords(scrape_url(url))
        # General exception handling
        except Exception as e:
            return f"Error during web scraping: {e}"
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
