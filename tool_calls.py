"""
This file contains the tool calls for the LLM
"""

import os
from openai import OpenAI
from dotenv import load_dotenv
from functions import scrape_url

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def get_web_scrape_tool() -> dict:
    """Returns the web scraping tool configuration for LLM."""
    return {
        "type": "function",
        "function": {
            "name": "web_scrape",
            "description": "Scrapes text content from a given URL, cleaning and limiting the output to 4000 characters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to scrape. Must be a valid HTTP/HTTPS URL."
                    }
                },
                "required": ["url"]
            }
        }
    }

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
                "truncated": len(scraped_text) >= 4000
            }
        }
    except Exception as e:
        return {
            "success": False,
            "text": None,
            "error": str(e),
            "metadata": None
        }

def web_scrape(url: str) -> dict:
    """
    This function scrapes a URL with an llm tool_call and returns the text.
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": f"Please scrape this webpage {url}"}],
        tools=[get_web_scrape_tool()],
        tool_choice="auto"
    )

    return response["choices"][0]["message"]["content"]

