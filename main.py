import requests
from flask import Flask, render_template, request

from functions import identify_keywords, scrape_url

app = Flask(__name__)


@app.route("/web_scraper/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        try:
            return identify_keywords(scrape_url(url))
        except:
            return "Error fetching URL"
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
