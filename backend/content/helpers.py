"""
Helper functions for the content_processor.py and search_retrieval.py files
"""

import json
import os
from uuid import UUID

from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI

from backend.content.content_processor import ContentProcessor
from backend.models.mongo.db_manager import MongoDBManager
from backend.models.rag.qdrant import QdrantVectorStore

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


# Retrieve context from Qdrant
async def get_relevant_context(
    query: str,
    tenant_id: UUID,
    collection_name: str = "web_content",
    qdrant_client: QdrantVectorStore = None,
) -> str:
    """
    Retrieve relevant context from Qdrant based on the query

    Args:
        query (str): The search query
        tenant_id (UUID): Tenant ID for filtering results
        collection_name (str): Name of the Qdrant collection

    Returns:
        str: Formatted context from relevant documents
    """
    try:
        if not qdrant_client:
            qdrant_client = QdrantVectorStore(tenant_id=tenant_id)
        search_results = qdrant_client.search_data_in_qdrant(
            collection_name=collection_name,
            query=query,
            tenant_id=tenant_id,
            limit=3,  # Limit to top 3 most relevant results
        )

        if not search_results:
            logger.info("No relevant context found in Qdrant")
            return None

        # Format the context from search results
        output_context = []
        input_context = []
        for i, result in enumerate(search_results):
            payload = result.payload

            # Extract cleaned LLM response and input headings from payload if available,
            # format them as JSON strings and append to respective context lists.
            # Log warning if payload structure is unexpected.
            if "content" in payload and isinstance(payload["content"], dict):
                if "cleaned_llm_response" in payload["content"]:
                    content = payload["content"]["cleaned_llm_response"]
                    output_context.append(json.dumps({f"Document {i+1}": content}))
                else:
                    logger.warning(f"Unexpected payload structure for Document {i+1}")
                if "input_headings" in payload["content"]:
                    headings = payload["content"]["input_headings"]
                    input_context.append(json.dumps({f"Document {i+1}": headings}))
                else:
                    logger.warning(f"Unexpected payload structure for Document {i+1}")
            else:
                logger.warning(f"Unexpected payload structure for Document {i+1}")

        return {
            "output_context": "\n\n".join(output_context),
            "input_context": "\n\n".join(input_context),
        }
    except Exception as e:
        logger.error(f"Error retrieving context from Qdrant: {str(e)}")
        return ""


# Call OpenAI API and handle exceptions
def call_openai_api(messages: list) -> dict:
    """
    Call OpenAI API
    """
    try:
        logger.info("Sending request to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            timeout=30,
        )
        return {
            "success": True,
            "llm_response": response.model_dump(),
        }
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {str(e)}")
        return {
            "success": False,
            "information": None,
            "storage_success": False,
            "error": f"Error during information identification: {str(e)}",
        }


# Store result in MongoDB and handle exceptions
async def store_result_in_mongodb(
    scrape_result: dict, cleaned_llm_response: dict, tenant_id: UUID
) -> dict:
    """
    Store the result in MongoDB
    """
    try:
        mongo_result = await MongoDBManager.insert_web_content(
            url=scrape_result["url"],
            raw_text=scrape_result["information"]["all_text"],
            headings=scrape_result["information"]["headings"],
            llm_cleaned_content=cleaned_llm_response,
            metadata=None,
            tenant_id=tenant_id,
        )
        logger.info(f"Successfully stored result in MongoDB: {mongo_result.id}")
        return {"success": True, "mongo_result": mongo_result}
    except Exception as e:
        logger.error(f"Error during MongoDB storage: {str(e)}")
        return {
            "success": False,
            "information": None,
            "storage_success": False,
            "error": f"Error during MongoDB storage: {str(e)}",
        }


# Store the list of vector payloads into Qdrant
async def add_payload_and_store_in_qdrant(
    processor: ContentProcessor,
    tenant_id: UUID,
    collection_name: str = "web_content",
    qdrant_client: QdrantVectorStore = None,
) -> dict:
    """
    Add payload and store in Qdrant

    Args:
        processor: ContentProcessor instance with payloads
        tenant_id: UUID of the tenant
        collection_name: Name of the Qdrant collection (default: "web_content")

    Returns:
        dict: {
            "success": bool,
            "storage_success": bool,
            "result": types.UpdateResult | None,
            "error": str | None
        }
    """
    try:
        logger.info("Preparing to store information in Qdrant...")
        if not qdrant_client:
            qdrant_client = QdrantVectorStore(tenant_id=tenant_id)

        vector_payloads = processor.get_payloads()
        result = qdrant_client.insert_data_to_qdrant(
            vector_payloads=vector_payloads, collection_name=collection_name
        )

        logger.info(f"Successfully stored information in Qdrant: {result}")
        return {
            "success": True,
            "storage_success": True,
            "result": result,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Error during Qdrant storage: {str(e)}")
        return {
            "success": False,
            "storage_success": False,
            "result": None,
            "error": f"Error during Qdrant storage: {str(e)}",
        }
