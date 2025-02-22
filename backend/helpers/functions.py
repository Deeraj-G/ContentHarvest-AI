"""
This file contains the functions for the web scraper.
"""

import os

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


# Scrape the URL and return the text
# Scrape based on bolded words (these are the most important words)
def scrape_url(url: str) -> str:
    """
    This function scrapes a URL and returns the text.
    """
    try:
        response = requests.get(url, timeout=10)  # 10 second timeout
        soup = BeautifulSoup(response.text, "html.parser")
        # Clean the text and limit length
        text = " ".join(soup.get_text().split())  # Remove extra whitespace
        text = text[:4000]  # Limit to 4000 characters
        return text
    except Exception as e:
        return f"Error during web scraping: {e}"


def web_scrape_wrapper(url: str) -> dict:
    """
    A wrapper function for the web scraping function.
    Return in a format more suitable for the LLM.

    Args:
        url (str): The URL to scrape

    Returns:
        dict: {
            "success": bool,
            "text": str | None,
            "error": str | None,
            "metadata": {
                "length": int,
                "truncated": bool
            }
        }
    """
    try:
        scraped_text = scrape_url(url)
        return {
            "success": True,
            "text": scraped_text,
            "error": None,
            "metadata": {
                "length": len(scraped_text),
                "truncated": len(scraped_text) >= 4000,
            },
        }
    except Exception as e:
        return {"success": False, "text": None, "error": str(e), "metadata": None}


# Query to LLM to identify the relevant information based on the text
def identify_keywords(text_wrapper: dict) -> dict:
    """
    This function identifies the keywords in the text and returns the information associated with each keyword.

    Args:
        text_wrapper (dict): The output from web_scrape_wrapper containing text and metadata

    Returns:
        dict: {
            "success": bool,
            "keywords": dict | None,  # Keyword information if successful
            "error": str | None,
            "metadata": {
                "source_length": int,
                "source_truncated": bool
            }
        }
    """
    # First check if the web scraping was successful
    if not text_wrapper["success"]:
        return {
            "success": False,
            "keywords": None,
            "error": f"Web scraping failed: {text_wrapper['error']}",
            "metadata": None,
        }

    # Static keywords for now
    keywords = ["History", "Components", "Features"]

    examples = [
        {
            "History": "The history of the company is that it started in 1990 and is a software company.",
            "Components": "The components of the product are HTML, CSS, and JavaScript built on Monolithic architecture.",
            "Features": "The features of the product are that it is lightweight, fast, and scalable.",
        },
        {
            "Images": [
                "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Dall-e_3_%28jan_%2724%29_artificial_intelligence_icon.png/200px-Dall-e_3_%28jan_%2724%29_artificial_intelligence_icon.png",
                "https://en.wikipedia.org/wiki/File:General_Formal_Ontology.svg",
            ],
            "Links": [
                "https://en.wikipedia.org/wiki/Knowledge_engineering",
                "https://en.wikipedia.org/wiki/Markov_decision_process",
            ],
            "Tags": ["h1", "h2", "h3", "h4", "h5", "h6"],
        },
    ]

    system_prompt = "You are a helpful assistant that identifies the information associated with given keywords."

    user_prompt = f"""
        Identify the information associate with each keyword: ```{keywords}``` from the following text: ```{text_wrapper["text"]}```.
        Return the information in a json with the format: ```keyword: relevant_information```.
        Use the examples as a guide: {examples}
    """

    messages = [
        {"role": "user", "content": user_prompt},
        {"role": "system", "content": system_prompt},
    ]

    # Call the LLM
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            timeout=30,  # 30 second timeout for AI response
        )

        response = response.model_dump()
        keywords_content = response["choices"][0]["message"]["content"]

        return {
            "success": True,
            "keywords": keywords_content,
            "error": None,
            "metadata": {
                "source_length": text_wrapper["metadata"]["length"],
                "source_truncated": text_wrapper["metadata"]["truncated"],
            },
        }
    except Exception as e:
        return {
            "success": False,
            "keywords": None,
            "error": f"Error during keyword identification: {e}",
            "metadata": text_wrapper["metadata"],
        }
