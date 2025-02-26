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
        all_text = soup.get_text(separator=" ")
        all_text = re.sub(r"\s+", " ", all_text)  # Remove extra whitespace

        headings = []

        # Find all headings within the url
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            heading_info = {
                "level": tag.name,  # Get heading level (1-6)
                "text": tag.get_text(strip=True),  # Get cleaned text content
                "id": tag.get("id", ""),  # Get id if exists (useful for anchor links)
            }

            # If there's a link inside the heading, capture it
            link = tag.find("a")
            if link:
                heading_info["link"] = link.get("href", "")

            headings.append(heading_info)

        result = {
            "success": True,
            "original_url": url,
            "all_text": all_text,
            "headings": headings,
            "metadata": {
                "text_length": len(all_text),
                "headings_count": len(headings),
                "truncated": len(all_text) >= 4000,
            },
            "error": None,
        }
        return result
    except Exception as e:
        return {
            "success": False,
            "original_url": url,
            "all_text": None,
            "headings": None,
            "metadata": None,
            "error": str(e),
        }


# Query to LLM to identify the relevant information based on the text
def relevant_information(scrape_result: dict) -> dict:
    """
    This function identifies relevant information from the text.

    Args:
        scrape_result (dict): The output from scrape_url containing text, links, and metadata

    Returns:
        dict: {
            "success": bool,
            "content": dict | None,  # Information if successful
            "error": str | None,
            "metadata": {
                "source_length": int,
                "source_truncated": bool,
                "links_count": int
            }
        }
    """
    # First check if the web scraping was successful
    if not scrape_result["success"]:
        return {
            "success": False,
            "content": f"Web scraping failed: {scrape_result['error']}",
            "metadata": None,
        }

    example_input = [{"level": "h1", "text": "Example Domain", "id": ""}]

    example_output = {
        "information": {
            "headings": {
                "Artificial Intelligence": "Artificial intelligence (AI), in its broadest sense, is intelligence exhibited by machines, particularly computer systems.",
                "Knowledge representation": "AI reasoning evolved from step-by-step logic to probabilistic methods, but scalability issues and the reliance on human intuition make efficient reasoning an unsolved challenge.",
            },
            "images": {
                "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Dall-e_3.png": "AI Icon"
            },
        }
    }

    system_prompt = "You are a helpful assistant that identifies the information associated with important `keywords`."

    user_prompt = f"""
        Identify important information (called `information`) from the following text: ```{scrape_result["all_text"][:4000]}```
        
        The page contains {len(scrape_result["headings"])} headings. Here are some relevant headings: ```{scrape_result["headings"][:10]}```
        
        Use the example input as a guide: ```{example_input}```
        
        Return the information in a json with the output format: ```{example_output}```
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Call the LLM
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            timeout=30,
        )

        response = response.model_dump()
        info_content = response["choices"][0]["message"]["content"]

        return {
            "success": True,
            "content": info_content,
            "metadata": scrape_result["metadata"],
        }
    except Exception as e:
        return {
            "success": False,
            "content": f"Error during info identification: {e}",
            "metadata": scrape_result["metadata"],
        }
