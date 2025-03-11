# Web Scraper

A simple web scraper that scrapes a URL and returns the keywords and their associated information.

## Usage

```bash
# Backend
uvicorn backend.fastapi_app.main:app --reload

# Frontend
cd frontend && npm start

# Execute a curl POST request to the server (without frontend)
curl -v http://localhost:8000/web_scraper/ -H "Content-Type: application/x-www-form-urlencoded" -d "url=https://en.wikipedia.org/wiki/Artificial_intelligence"
```
