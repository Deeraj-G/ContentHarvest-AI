"""
Core functionality of the content processor.

Key features:
- Scraping web pages to extract relevant text and headings.
- Vectorizing the scraped content for efficient search and retrieval.
- Storing the raw and processed content in a MongoDB database.
- Managing interactions with the Qdrant vector store for search capabilities.

Essential for building a content ingestion pipeline that transforms raw web data into structured, searchable information.
"""

import os
import re
from uuid import UUID

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from loguru import logger

from backend.models.rag.qdrant import QdrantVectorStore
from backend.services.vector_schemas import ContentProcessor
from backend.models.mongo.db_manager import MongoDBManager
from backend.content.prompts import get_prompts


TEXT_LIMIT = 4000
HEADING_LIMIT = 10

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
            "success": True,
            "information": {"all_text": all_text, "headings": headings},
            "url": url,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Error scraping URL {url}: {str(e)}")
        return {
            "success": False,
            "information": None,
            "url": url,
            "error": str(e),
        }


# Query to LLM to identify the relevant information based on the text
async def vectorize_and_store_web_content(
    scrape_result: dict, tenant_id: UUID = None
) -> dict:
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
            collected_headings[level] = scrape_result["information"]["headings"][level][:HEADING_LIMIT - len(collected_headings)]
            if len(collected_headings) >= HEADING_LIMIT:
                break

    system_prompt, user_prompt = get_prompts(
        headings_subset=collected_headings,
        limited_text=scrape_result["information"]["all_text"][:TEXT_LIMIT],
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        logger.info("Sending request to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            timeout=30,
        )

        llm_response = response.model_dump()
        logger.info(
            f"Successfully received and processed OpenAI response: {llm_response}"
        )

        # Clean the LLM response
        cleaned_llm_response = llm_response["choices"][0]["message"]["content"].replace("```json", "").replace("```", "").strip()

        logger.info(f"Cleaned LLM response: {cleaned_llm_response}")

        # Store full result in MongoDB
        mongo_result = await MongoDBManager.insert_web_content(
            url=scrape_result["url"],
            raw_text=scrape_result["information"]["all_text"],
            headings=scrape_result["information"]["headings"],
            llm_cleaned_content=cleaned_llm_response,
            metadata=scrape_result["metadata"],
            tenant_id=tenant_id,
        )

        logger.info(f"Successfully stored result in MongoDB: {mongo_result.id}")

        # Add the LLM processed result
        processor.add_payload(
            content={
                "cleaned_llm_response": cleaned_llm_response,
                "input_text": scrape_result["information"]["all_text"][:TEXT_LIMIT],
                "input_headings": collected_headings,
                "mongo_id": str(mongo_result.id),
            },
            url=scrape_result["url"],
        )

        logger.info("Successfully added payload to processor")

        qdrant_storage_result = vectorize_information_to_qdrant(
            vector_payloads=processor.get_payloads(),
            tenant_id=tenant_id,
            collection_name="web_content",
        )

        logger.info("Storing information in Qdrant...")

        return {
            "success": True,
            "cleaned_llm_response": cleaned_llm_response,
            "storage_success": qdrant_storage_result["success"],
            "error": None,
        }
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {str(e)}")

        # Store full content in MongoDB
        mongo_result = await MongoDBManager.insert_web_content(
            url=scrape_result["url"],
            raw_text=scrape_result["information"]["all_text"],
            headings=scrape_result["information"]["headings"],
            llm_cleaned_content=None,
            metadata=scrape_result["metadata"],
            tenant_id=tenant_id,
        )

        logger.debug(f"Stored error information in MongoDB: {mongo_result.id}")

        # Add the LLM processed result
        processor.add_payload(
            content={
                "cleaned_llm_response": None,
                "input_text": scrape_result["information"]["all_text"][:TEXT_LIMIT],
                "input_headings": collected_headings,
                "mongo_id": str(mongo_result.id),
            },
            url=scrape_result["url"],
        )

        logger.debug("Successfully added payload to processor")

        qdrant_storage_result = vectorize_information_to_qdrant(
            vector_payloads=processor.get_payloads(),
            tenant_id=tenant_id,
            collection_name="web_content",
        )

        logger.debug("Storing information in Qdrant...")

        return {
            "success": False,
            "information": None,
            "storage_success": qdrant_storage_result["success"],
            "error": f"Error during information identification: {str(e)}",
        }


# Store the list of vector payloads into Qdrant
def vectorize_information_to_qdrant(
    vector_payloads: list, collection_name: str, tenant_id: str = None
) -> dict:
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
        logger.info("Preparing to store information in Qdrant...")
        qdrant_client = QdrantVectorStore(tenant_id=tenant_id)

        info = qdrant_client.insert_data_to_qdrant(
            vector_payloads=vector_payloads, collection_name=collection_name
        )
        logger.info(f"Successfully stored information in Qdrant: {info}")
        return {"success": True, "info": info, "error": None}
    except Exception as e:
        logger.error(f"Failed to store information in Qdrant with error: {str(e)}")
        return {"success": False, "info": None, "error": str(e)}
