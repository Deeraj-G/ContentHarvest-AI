"""
This file contains the functions for the web scraper.
"""

import os
import re

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
    Scrapes a URL and returns the content with metadata.

    Args:
        url (str): The URL to scrape

    Returns:
        dict: {
            "success": bool,
            "url": str,
            "all_text": str,
            "links": list[dict],
            "metadata": {
                "text_length": int,
                "links_count": int,
                "truncated": bool
            },
            "error": str | None
        }
    """
    try:
        response = requests.get(url, timeout=10)  # 10 second timeout
        soup = BeautifulSoup(response.text, "html.parser")
        # Clean the text and limit length
        all_text = soup.get_text(separator=" ")
        all_text = re.sub(r"\s+", " ", all_text) # Remove extra whitespace

        links = []

        # Find all links within the url with href or src
        for tag in soup.find_all(["a", "link"]):
            link_info = {}
            href = tag.get("href")
            src = tag.get("src")

            if href:
                link_info["url"] = href
                link_info["text"] = tag.text
            elif src:
                link_info["url"] = src
                link_info["text"] = tag.text
            
            if link_info:
                common = ["title", "rel"]
                for attr in common:
                    value = tag.get(attr)
                    if value:
                        link_info[attr] = value

                links.append(link_info)

        result = {
            "success": True,
            "original_url": url,
            "all_text": all_text,
            "links": links,
            "metadata": {
                "text_length": len(all_text),
                "links_count": len(links),
                "truncated": len(all_text) >= 4000
            },
            "error": None
        }
        return result
    except Exception as e:
        return {
            "success": False,
            "original_url": url,
            "all_text": None,
            "links": None,
            "metadata": None,
            "error": str(e)
        }


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
        Identify the information associate with each keyword: ```{keywords}``` from the following text: ```{text_wrapper["text"][:4000]}```.
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
