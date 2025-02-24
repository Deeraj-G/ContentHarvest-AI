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
        all_text = re.sub(r"\s+", " ", all_text)  # Remove extra whitespace

        headings = []

        # Find all headings within the url
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            heading_info = {
                "level": int(tag.name[1]),  # Get heading level (1-6)
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
    This function identifies the keywords in the text and returns the information associated with each keyword.

    Args:
        scrape_result (dict): The output from scrape_url containing text, links, and metadata

    Returns:
        dict: {
            "success": bool,
            "keywords": dict | None,  # Keyword information if successful
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
            "keywords": None,
            "error": f"Web scraping failed: {scrape_result['error']}",
            "metadata": None,
        }

    example_input = [
        {
            "url": "https://en.wikipedia.org/wiki/Knowledge_engineering",
            "text": "Knowledge engineering",
            "title": "Learn more about knowledge engineering"
        },
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Dall-e_3.png",
            "text": "AI Icon",
            "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Dall-e_3.png"
        }
    ]

    example_output = [
        {
            "content": {
                "Content Analysis": "The content appears to focus on artificial intelligence and knowledge engineering concepts. The presence of DALL-E 3 imagery suggests a focus on generative AI technologies.",
                "Key Topics": "The main topics covered include knowledge engineering, Markov decision processes, and formal ontology structures, indicating this is likely technical or academic content.",
                "Visual Elements": "The page contains AI-related imagery, including a DALL-E 3 icon and a diagram showing General Formal Ontology structures.",
            },
        }
    ]

    system_prompt = "You are a helpful assistant that identifies the information associated with important `keywords`."

    user_prompt = f"""
        Identify important information (called `keywords`) from the following text: ```{scrape_result["all_text"][:4000]}```.
        The page contains {len(scrape_result["headings"])} headings. Here are some relevant headings: {scrape_result["headings"][:10]}
        Return the information in a json with the format: ```keyword: relevant_information```.
        Use the example input and output as a guide: {example_input} and {example_output}
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
            timeout=30,  # 30 second timeout for AI response
        )

        response = response.model_dump()
        keywords_content = response["choices"][0]["message"]["content"]

        return {
            "success": True,
            "keywords": keywords_content,
            "error": None,
            "metadata": {
                "source_length": scrape_result["metadata"]["text_length"],
                "source_truncated": scrape_result["metadata"]["truncated"],
                "headings_count": scrape_result["metadata"]["headings_count"],
            },
        }
    except Exception as e:
        return {
            "success": False,
            "keywords": None,
            "error": f"Error during keyword identification: {e}",
            "metadata": scrape_result["metadata"],
        }
