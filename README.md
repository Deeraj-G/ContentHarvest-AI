# Web Scraper

A simple web scraper that scrapes a URL and returns the keywords and their associated information.

## Usage

```bash
# Run the server
python main.py

# Execute a curl POST request to the server
curl -v http://localhost:8000/web_scraper/ -H "Content-Type: application/x-www-form-urlencoded" -d "url=https://en.wikipedia.org/wiki/Artificial_intelligence"
```



## TODO

- [ ] Add a way to scrape based on the html tags, css selectors, images, and links
- [ ] Accept keywords via the curl command