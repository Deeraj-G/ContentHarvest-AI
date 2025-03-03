"""
This file contains the functions for the web scraper.
"""

import os
import re
from uuid import UUID

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from loguru import logger

from backend.rag.qdrant import QdrantVectorStore
from backend.services.vector_schemas import ContentProcessor
from backend.models.mongo.db_manager import MongoDBManager


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

TEXT_LIMIT = 4000
HEADING_LIMIT = 10


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
        logger.info(f"Response status code: {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")
        all_text = soup.get_text(separator=" ")
        all_text = re.sub(r"\s+", " ", all_text)
        logger.info(f"Extracted text length: {len(all_text)}")

        headings = []

        # Find all headings within the url
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            title = tag.get_text(strip=True)  # Get cleaned title content
            level = tag.name  # Get heading level (h1-h6)

            headings.append({title: level})

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

    # If the web scraping failed, return the error
    if not scrape_result["success"]:
        logger.error(
            f"Cannot process information - web scraping failed: {scrape_result['error']}"
        )
        return {
            "success": False,
            "information": None,
            "storage_success": False,
            "error": f"Web scraping failed: {scrape_result['error']}",
        }

    # Prepare and store vectors in Qdrant
    processor = ContentProcessor(tenant_id=tenant_id)

    system_prompt, user_prompt = get_prompts(scrape_result)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Call LLM
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

        information_content = llm_response["choices"][0]["message"]["content"]

        # Clean and parse the LLM response
        cleaned_content = (
            information_content.replace("```json", "").replace("```", "").strip()
        )
        logger.info(f"Cleaned content: {cleaned_content}")

        # Store full content in MongoDB
        mongo_result = await MongoDBManager.insert_web_content(
            url=scrape_result["original_url"],
            raw_text=scrape_result["all_text"],
            headings=scrape_result["headings"],
            llm_raw_response=llm_response,
            processed_content=cleaned_content,
            metadata=scrape_result["metadata"],
            tenant_id=tenant_id,
        )

        logger.info(f"Successfully stored information in MongoDB: {mongo_result.id}")

        # Add the LLM processed result
        processor.add_payload(
            content={
                "llm_response": cleaned_content,
                "all_text": scrape_result["information"]["all_text"][:TEXT_LIMIT],
                "headings": scrape_result["information"]["headings"][:HEADING_LIMIT],
                "mongo_id": str(mongo_result.id),
            },
            url=scrape_result["original_url"],
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
            "information": cleaned_content,
            "storage_success": qdrant_storage_result["success"],
            "error": None,
        }
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {str(e)}")

        # Store full content in MongoDB
        mongo_result = await MongoDBManager.insert_web_content(
            url=scrape_result["original_url"],
            raw_text=scrape_result["all_text"],
            headings=scrape_result["headings"],
            llm_raw_response=None,
            processed_content=None,
            metadata=scrape_result["metadata"],
            tenant_id=tenant_id,
        )

        logger.debug(f"Stored error information in MongoDB: {mongo_result.id}")

        # Add the LLM processed result
        processor.add_payload(
            content={
                "llm_response": None,
                "all_text": scrape_result["information"]["all_text"][:TEXT_LIMIT],
                "headings": scrape_result["information"]["headings"][:HEADING_LIMIT],
                "mongo_id": str(mongo_result.id),
            },
            url=scrape_result["original_url"],
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


def get_prompts(scrape_result: dict):
    """
    Static system prompt for the LLM
    """

    example_raw_text = """
    Introduction to Machine Learning ( ML ) represents a fundamental shift in how computers operate. Instead of following explicit programming instructions, these systems learn patterns from data. This revolutionary approach has transformed various industries and continues to drive innovation in technology. The field combines statistics, computer science, and data analysis to create powerful predictive models.

    Among the various approaches in machine learning, Supervised Learning Methods stands as one of the most widely used techniques. In this method, algorithms learn from labeled datasets where the desired output is known. For instance, when training a model to recognize spam emails, we provide examples of both spam and legitimate emails. The algorithm learns to identify patterns and features that distinguish between these categories. Common algorithms include decision trees, which make sequential decisions based on data features, and support vector machines, which find optimal boundaries between different classes of data.

    The impact of Deep Learning Applications on modern technology cannot be overstated. In healthcare, deep learning models analyze medical images to detect diseases with remarkable accuracy. Self-driving cars use deep learning to interpret their environment and make real-time decisions. Natural language processing applications powered by deep learning have made machine translation and voice assistants part of our daily lives.

    Neural Networks and Deep Learning are at the core of these advances. These networks consist of layers of interconnected nodes, each performing specific computations. The \" deep \" in deep learning refers to the multiple layers that allow these networks to learn increasingly complex features. For example, in image recognition, early layers might detect simple edges, while deeper layers recognize complex objects like faces or vehicles.
    """

    example_input = [
        {"Introduction to Machine Learning": "h1"},
        {"Supervised Learning Methods": "h2"},
        {"Deep Learning Applications": "h3"},
        {"Neural Networks and Deep Learning": "h2"},
    ]

    example_output = {
        "information": {
            "headings": {
                "Introduction to Machine Learning": "Machine learning represents a fundamental shift in how computers operate, enabling systems to learn patterns from data rather than following explicit programming instructions. This field combines statistics, computer science, and data analysis to create powerful predictive models.",
                "Supervised Learning Methods": "Supervised learning algorithms learn from labeled datasets where the desired output is known, using techniques like decision trees and support vector machines to identify patterns and make predictions. This approach is widely used for classification tasks like spam detection.",
                "Deep Learning Applications": "Deep learning has revolutionized multiple sectors, from healthcare (medical image analysis) to autonomous vehicles and natural language processing, enabling sophisticated real-time decision making and analysis.",
                "Neural Networks and Deep Learning": "Neural networks are mathematical models inspired by the human brain, consisting of multiple layers of interconnected nodes that process information with increasing complexity. These layers progress from detecting simple features to recognizing complex patterns in data.",
            }
        }
    }

    system_prompt = """
        You are a professional content analyst and information specialist who excels at extracting key information from documents.
    
        You are provided with both the full text and a structured list of headings from the document.
    
        Your role is to carefully analyze the content under each heading and produce clear, concise summaries that capture the essential information and main points.
    """

    user_prompt = f"""
        Your task is to analyze the following text and extract key information for each heading:

        ### CURRENT CONTENT TO ANALYZE ###
        TEXT: {scrape_result["information"]["all_text"][:TEXT_LIMIT]}

        HEADINGS: The document contains {len(scrape_result["information"]["headings"])} headings. 
        First {HEADING_LIMIT} headings for reference: ```{scrape_result["information"]["headings"][:HEADING_LIMIT]}```

        ### EXAMPLES ###
        EXAMPLE RAW TEXT:
        {example_raw_text}

        EXAMPLE INPUT:
        {example_input}

        EXAMPLE OUTPUT:
        {example_output}

        ### REQUIREMENTS ###
        For each heading:
        1. Create a clear, factually accurate summary (1-2 sentences) that captures key points
        2. Prioritize content based on heading importance (h1 > h2 > h3 etc.)
        3. Ensure output follows the exact JSON structure shown in the example
        4. Exclude any additional text or formatting
    """

    logger.info(f"System Prompt: {system_prompt}")
    logger.info(f"User Prompt: {user_prompt}")

    return system_prompt, user_prompt
