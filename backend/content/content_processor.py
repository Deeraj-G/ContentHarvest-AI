"""
Core functionality of the content processor.

Key features:
- Scraping web pages to extract relevant text and headings.
- Vectorizing the scraped content for efficient search and retrieval.
- Storing the raw and processed content in a MongoDB database.
- Managing interactions with the Qdrant vector store for search capabilities.

Essential for building a content ingestion pipeline that transforms raw web data into structured, searchable information.
"""

import json
import os
import re
from uuid import UUID

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI

from backend.content.prompts import get_prompts
from backend.services.vector_schemas import ContentProcessor
from backend.content.helpers import (
    get_relevant_context,
    call_openai_api,
    store_result_in_mongodb,
    add_payload_and_store_in_qdrant,
)

TEXT_LIMIT = 6000
HEADING_LIMIT = 6

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


# Scrape the URL and return the text
async def scrape_url(url: str) -> dict:
    """
    Scrapes a URL and returns the content with metadata.

    Args:
        url (str): The URL to scrape

    Returns:
        dict: {
            "url": str,
            "information": dict | None,
            "success": bool,
            "error": str | None
        }
    """
    logger.info("starting to scrape URL")
    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            logger.error(f"Failed to harvest URL {url}: {response.status_code}")
            return {
                "url": url,
                "information": None,
                "success": False,
                "error": f"Failed to harvest URL: {url}",
                "status_code": response.status_code,
            }
        soup = BeautifulSoup(response.text, "html.parser")
        all_text = soup.get_text(separator=" ")
        all_text = re.sub(r"\s+", " ", all_text)

        # Initialize the headings dictionary with buckets for each heading level
        headings = {"h1": [], "h2": [], "h3": [], "h4": [], "h5": [], "h6": []}

        # Find all headings within the url
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            title = tag.get_text(strip=True)  # Get cleaned title content
            level = tag.name  # Get heading level (h1-h6)

            headings[level].append(title)

        return {
            "url": url,
            "information": {"all_text": all_text, "headings": headings},
            "success": True,
            "error": None,
            "status_code": response.status_code,
        }

    except Exception as e:
        logger.error(f"Error harvesting URL {url}: {str(e)}")
        return {
            "url": url,
            "information": None,
            "success": False,
            "error": str(e),
            "status_code": response.status_code,
        }


# Query to LLM to identify the relevant information based on the text
async def vectorize_and_store_web_content(scrape_result: dict, tenant_id: UUID) -> dict:
    """
    Store content in both MongoDB and Qdrant.
    MongoDB gets the full content, Qdrant gets the vectors for search.
    """
    logger.info("Starting information identification")

    # Prepare and store vectors in Qdrant
    processor = ContentProcessor(tenant_id=tenant_id)
    collected_headings = {}

    # Add all headings from most important to least important
    for level in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        if level in scrape_result["information"]["headings"]:
            collected_headings[level] = scrape_result["information"]["headings"][level][
                : HEADING_LIMIT - len(collected_headings)
            ]
            if len(collected_headings) >= HEADING_LIMIT:
                break

    # Get query text from headings or URL
    query_text = ""
    if collected_headings.get("h1") and collected_headings["h1"]:
        query_text = collected_headings["h1"][0]
    elif scrape_result["url"]:
        query_text = scrape_result["url"]

    # Get relevant context if we have a query
    relevant_context = ""
    if query_text:
        relevant_context = await get_relevant_context(query_text, tenant_id)

    # Get prompts with relevant context
    system_prompt, user_prompt = get_prompts(
        headings_subset=collected_headings,
        limited_text=scrape_result["information"]["all_text"][:TEXT_LIMIT],
        output_context=relevant_context["output_context"],
        input_context=relevant_context["input_context"],
    )

    logger.info(f"System prompt: {system_prompt}")
    logger.info(f"User prompt: {user_prompt}")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Call OpenAI API
    response = call_openai_api(messages)
    if "success" not in response or not response["success"]:
        return response

    # Clean the LLM response
    llm_response = response["llm_response"]["choices"][0]["message"]["content"]
    logger.info(f"LLM response: {llm_response}")
    cleaned_llm_response = (
        llm_response.replace("```json", "").replace("```", "").strip()
    )
    try:
        cleaned_llm_response = json.loads(cleaned_llm_response)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing LLM response as JSON: {str(e)}")
        return {
            "success": False,
            "information": None,
            "storage_success": False,
            "error": f"Error parsing LLM response as JSON: {str(e)}",
        }
    logger.info(f"Cleaned LLM response: {cleaned_llm_response}")

    # Store result in MongoDB
    mongo_result_response = await store_result_in_mongodb(
        scrape_result, cleaned_llm_response, tenant_id
    )
    if "success" not in mongo_result_response or not mongo_result_response["success"]:
        return mongo_result_response

    # Add the LLM processed result
    processor.add_payload(
        content={
            "cleaned_llm_response": cleaned_llm_response,
            "input_text": scrape_result["information"]["all_text"][:TEXT_LIMIT],
            "input_headings": collected_headings,
            "mongo_id": str(mongo_result_response["mongo_result"].id),
        },
        url=scrape_result["url"],
    )

    logger.info("Successfully added payload to processor")

    # Store in Qdrant
    qdrant_response = await add_payload_and_store_in_qdrant(processor, tenant_id)

    if "success" not in qdrant_response or not qdrant_response["success"]:
        return {
            "success": False,
            "information": cleaned_llm_response,
            "storage_success": False,
            "error": qdrant_response["error"],
        }

    return {
        "success": True,
        "information": cleaned_llm_response,
        "storage_success": qdrant_response["storage_success"],
        "error": None,
    }
