"""
This file contains the functions for the web scraper.
"""

import os
import re

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from loguru import logger
from uuid import UUID
from rag.qdrant import QdrantVectorStore
from backend.models.models import ContentProcessor


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
            }

            # If there's a link inside the heading, capture it
            link = tag.find("a")
            if link:
                heading_info["link"] = link.get("href", "")

            headings.append(heading_info)

        logger.info(f"Successfully scraped URL: {url}")

        return {
            "success": True,
            "information": {"all_text": all_text, "headings": headings},
            "original_url": url,
            "error": None,
        }
        
    except Exception as e:
        logger.error(f"Error scraping URL {url}: {str(e)}")
        return {
            "success": False,
            "information": None,
            "original_url": url,
            "error": str(e)
        }


# Query to LLM to identify the relevant information based on the text
def relevant_information(scrape_result: dict, tenant_id: UUID=None) -> dict:
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
            "error": str | None
        }
    """

    if not scrape_result["success"]:
        logger.error(f"Cannot process information - web scraping failed: {scrape_result['error']}")
        return {
            "success": False,
            "information": None,
            "storage_success": False,
            "error": f"Web scraping failed: {scrape_result['error']}"
        }

    logger.info("Starting information identification")
    
    processor = ContentProcessor(tenant_id=tenant_id)

    # If the web scraping failed, return the error
    if not scrape_result["success"]:
        logger.error(f"Cannot process information - web scraping failed: {scrape_result['error']}")
        return {
            "success": False,
            "information": None,
            "storage_success": False,
            "error": f"Web scraping failed: {scrape_result['error']}"
        }

    # Example input and output
    example_input = [{"level": "h1", "text": "Artificial Intelligence", "id": ""}]

    example_output = {
        "information": {
            "headings": {
                "Artificial Intelligence": "Artificial intelligence (AI), in its broadest sense, is intelligence exhibited by machines, particularly computer systems.",
                "Knowledge representation": "AI reasoning evolved from step-by-step logic to probabilistic methods, but scalability issues and the reliance on human intuition make efficient reasoning an unsolved challenge.",
            }
        }
    }

    system_prompt = """
        You are an expert at identifying the most important information from given text. 
    
        You are also given a list of headings. 
    
        Your job is to identify and summarize the information associated with each heading.
    """

    user_prompt = f"""
        Identify important information belonging to each heading from the following text: ```{scrape_result["information"]["all_text"][:4000]}```
        
        The page contains {len(scrape_result["information"]["headings"])} headings. Here are the first 10 headings: ```{scrape_result["information"]["headings"][:10]}```
        
        Use the example input as a guide: ```{example_input}```
        
        Return the information in a json with the output format: ```{example_output}```

        Use your knowledge and judgement to identify the most important information for each heading.
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

        llm_response = response.model_dump()
        logger.info(f"Successfully received and processed OpenAI response: {llm_response}")

        information_content = llm_response["choices"][0]["message"]["content"]

        # Clean and parse the LLM response
        cleaned_content = information_content.replace("```json", "").replace("```", "").strip()
        logger.info(f"Cleaned content: {cleaned_content}")

        # Add the LLM result
        processor.add_payload(
            content={
                "llm_response": cleaned_content, 
                "all_text": scrape_result["information"]["all_text"], 
                "headings": scrape_result["information"]["headings"]
            },
            url=scrape_result["original_url"]
        )

        storage_result = store_information_in_qdrant(
            vector_payloads=processor.get_payloads(),
            tenant_id=tenant_id,
            collection_name="web_content"
        )

        return {
            "success": True,
            "information": cleaned_content,
            "storage_success": storage_result["success"],
            "error": None
        }
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {str(e)}")

        storage_result = store_information_in_qdrant(
            vector_payloads=processor.get_payloads(),
            tenant_id=tenant_id,
            collection_name="web_content"
        )

        return {
            "success": False,
            "information": None,
            "storage_success": storage_result["success"],
            "error": f"Error during information identification: {str(e)}"
        }


# Store the list of vector payloads into Qdrant
def store_information_in_qdrant(vector_payloads: list, collection_name: str, tenant_id: str=None) -> dict:
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
        logger.debug("Preparing to store information in Qdrant")
        qdrant_client = QdrantVectorStore(tenant_id=tenant_id)
        
        info = qdrant_client.insert_data_to_qdrant(
            vector_payloads=vector_payloads,
            collection_name=collection_name
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