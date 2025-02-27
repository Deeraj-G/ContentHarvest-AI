"""
This file contains the functions for the web scraper.
"""

import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from loguru import logger

from rag.qdrant import QdrantVectorStore


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


# Scrape the URL and return the text
# Scrape based on bolded words (these are the most important words)
def scrape_url(url: str) -> dict:
    """
    Scrapes a URL and returns the content with metadata.

    Args:
        url (str): The URL to scrape

    Returns:
        dict: {
            "success": bool,
            "original_url": str,
            "all_text": str | None,
            "headings": list | None,
            "metadata": dict | None,
            "error": str | None
        }
    """
    logger.info(f"Starting to scrape URL: {url}")
    try:
        response = requests.get(url, timeout=10)
        logger.debug(f"Response status code: {response.status_code}")
        
        soup = BeautifulSoup(response.text, "html.parser")
        all_text = soup.get_text(separator=" ")
        all_text = re.sub(r"\s+", " ", all_text)
        logger.debug(f"Extracted text length: {len(all_text)}")

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
        logger.error(f"Error scraping URL {url}: {str(e)}")
        return {
            "success": False,
            "original_url": url,
            "all_text": None,
            "headings": None,
            "metadata": None,
            "error": str(e)
        }


def store_information_in_qdrant(information: dict, url: str, tenant_id: str=None) -> dict:
    """
    Store the processed information in Qdrant

    Returns:
        dict: {
            "success": bool,
            "info": dict | None,
            "error": str | None
        }
    """
    try:
        logger.debug(f"Preparing to store information from {url} in Qdrant")
        qdrant_client = QdrantVectorStore(tenant_id=tenant_id)
        
        vector_payload = [{
            "vector": [1.0] * 1536,  # Placeholder vector
            "payload": {
                "url": url,
                "tenant_id": tenant_id,
                "information": information,
                "timestamp": datetime.now().isoformat()
            }
        }]
        
        info = qdrant_client.insert_data_to_qdrant(
            collection_name="web_content",
            vector_payload=vector_payload
        )
        logger.info(f"Successfully stored information in Qdrant: {info}")
        return {
            "success": True,
            "info": info,
            "error": None
        }
    except Exception as e:
        logger.error(f"Failed to store information in Qdrant: {str(e)}")
        return {
            "success": False,
            "info": None,
            "error": str(e)
        }


# Query to LLM to identify the relevant information based on the text
def relevant_information(scrape_result: dict, tenant_id: str = None) -> dict:
    """
    This function identifies relevant information from the text and stores it in Qdrant before querying the LLM.

    Args:
        scrape_result (dict): The output from scrape_url containing text, links, and metadata
        tenant_id (str): The tenant ID for Qdrant

    Returns:
        dict: {
            "success": bool,
            "information": dict | None,
            "storage_success": bool,
            "metadata": dict | None,
            "error": str | None
        }
    """
    logger.info("Starting information identification")
    
    if not scrape_result["success"]:
        logger.error(f"Cannot process information - web scraping failed: {scrape_result['error']}")
        return {
            "success": False,
            "information": None,
            "storage_success": False,
            "metadata": None,
            "error": f"Web scraping failed: {scrape_result['error']}"
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
        logger.debug("Sending request to OpenAI")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            timeout=30,
        )

        response = response.model_dump()
        information_content = response["choices"][0]["message"]["content"]
        logger.info("Successfully received and processed OpenAI response")

        # Store the results in Qdrant
        storage_success = store_information_in_qdrant(
            information=information_content,
            url=scrape_result["original_url"],
            tenant_id=tenant_id
        )

        return {
            "success": True,
            "information": information_content,
            "storage_success": storage_success["success"],
            "metadata": {
                "source_length": scrape_result["metadata"]["text_length"],
                "source_truncated": scrape_result["metadata"]["truncated"],
                "headings_count": scrape_result["metadata"]["headings_count"],
            },
            "error": None
        }
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {str(e)}")
        return {
            "success": False,
            "information": None,
            "storage_success": False,
            "metadata": scrape_result["metadata"],
            "error": f"Error during information identification: {str(e)}"
        }
