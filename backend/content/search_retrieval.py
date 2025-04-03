"""
Retrieve relevant content from Qdrant for a specific tenant.
"""
from uuid import UUID
import asyncio

from dotenv import load_dotenv
from loguru import logger

from backend.models.rag.qdrant import QdrantVectorStore
from backend.services.embedding_utils import get_embedding

from backend.content.helpers import call_openai_api


load_dotenv()


async def search_retrieval(search_query: str, tenant_id: UUID) -> dict:
    """
    Retrieve relevant content from Qdrant for a specific tenant, summarize it using AI,
    and return the result.

    Args:
        search_query: The search query to retrieve content for
        tenant_id: The UUID of the tenant

    Returns:
        dict: Result of the retrieval and summarization operation.
              Includes 'success' (bool), 'summary' (str), 'retrieved_context' (list of raw search results),
              or 'error' (str) on failure.
    """
    try:
        logger.info(f"Starting search retrieval for query: '{search_query}' and tenant: {tenant_id}")

        # Initialize Qdrant client
        qdrant_client = QdrantVectorStore(tenant_id=tenant_id)

        # Step 2.2: Search Qdrant (internally handles Step 2.1: embedding)
        logger.info("Searching Qdrant collection 'web_content'...")
        search_results = await asyncio.to_thread(
            qdrant_client.search_data_in_qdrant,
            collection_name="web_content",
            query=search_query,
            tenant_id=tenant_id,
            limit=3
        )

        if not search_results:
            logger.info("No relevant documents found in Qdrant.")
            # Step 3: Return result
            return {"success": True, "summary": "No relevant information found for your query."}

        # Format context for summarization from search result payloads
        retrieved_context_list = []
        for i, result in enumerate(search_results):
            payload = result.payload

            logger.info(f"Payload: {payload}")

            information = payload["content"]["cleaned_llm_response"]["information"]


            if information and isinstance(information, dict):
                retrieved_context_list.append(f"Source {i+1}:\n contains the following information:{information}\n")
            else:
                logger.warning(f"Document {result.id} payload structure unexpected or missing 'cleaned_llm_response': {payload}")

        if not retrieved_context_list:
            logger.warning("No usable text content extracted from retrieved documents for summarization.")
            # Step 3: Return result - indicate docs found but no content
            return {"success": True, "summary": "Found related documents, but could not extract text content to generate a summary."} # Return raw results

        formatted_context = "\n\n---\n\n".join(retrieved_context_list)
        logger.debug(f"Formatted context for summarization:\n{formatted_context[:500]}...") # Log snippet

        # Step 2.3: Use AI to summarize the findings
        logger.info("Sending context to LLM for summarization...")
        messages = [
            {"role": "system", "content": "You are an AI assistant. Summarize the provided text concisely, based on the user's query."},
            {"role": "user", "content": f"User Query: '{search_query}'\n\nPlease summarize the following information:\n\n{formatted_context}"}
        ]

        openai_response = await asyncio.to_thread(call_openai_api, messages=messages)

        if not openai_response or not openai_response.get("success"):
            error_msg = openai_response.get('error', 'Unknown API error') if openai_response else 'No response from API call'
            logger.error(f"LLM summarization failed: {error_msg}")
            # Step 3: Return error, include raw context
            return {"success": False, "error": f"Failed to summarize findings: {error_msg}"}

        # Extract summary safely
        try:
            # Accessing the nested structure based on OpenAI's usual response format
            summary = openai_response["llm_response"]["choices"][0]["message"]["content"].strip()
            if not summary:
                raise ValueError("LLM returned an empty summary.")
            logger.info("Successfully received summary from LLM.")
        except (KeyError, IndexError, TypeError, AttributeError, ValueError) as e:
            logger.error(f"Failed to parse summary from LLM response: {e}. Response: {openai_response.get('llm_response')}")
            # Step 3: Return error, include raw context
            return {"success": False, "error": "Failed to parse summary from LLM response."}


        # Step 2.4: Store the AI result back into Qdrant
        # logger.warning("Step 2.4 (Store summary in Qdrant) is marked in the plan but not implemented due to ambiguity.")
        # Placeholder for potential future implementation:
        # await store_summary_in_qdrant(tenant_id, search_query, summary, [r.id for r in search_results])
        try:
            logger.info("Attempting to store generated summary back into Qdrant...")
            # Generate embedding for the summary itself
            summary_embedding = await asyncio.to_thread(get_embedding, summary)

            # Prepare payload for the summary
            summary_payload = {
                "type": "generated_summary", # Add a type to distinguish it
                "summary_text": summary,
                "original_query": search_query,
                "source_document_ids": [str(result.id) for result in search_results] # Store IDs of source docs
            }

            # Structure for insert_data_to_qdrant
            vector_payloads_to_store = [{
                "vector": summary_embedding,
                "payload": summary_payload
            }]

            # Store the summary vector and payload (using the same client instance)
            # Note: insert_data_to_qdrant handles adding tenant_id and session_id internally
            storage_result = await asyncio.to_thread(
                qdrant_client.insert_data_to_qdrant,
                vector_payloads=vector_payloads_to_store,
                collection_name="web_content"
            )
            logger.info(f"Successfully stored summary in Qdrant. Result: {storage_result}")

        except Exception as store_exc:
            # Log the error but proceed to return the summary to the user
            logger.error(f"Failed to store summary back into Qdrant: {store_exc}", exc_info=True)
            # Decide if this failure should make the overall operation fail.
            # For now, we log it and continue, as the user still gets their summary.


        # Step 3: Return the successful result to the user
        return {
            "success": True,
            "summary": summary,
        }

    except Exception as e:
        logger.exception(f"An unexpected error occurred during search retrieval for tenant {tenant_id}: {str(e)}")
        # Step 3: Return comprehensive error
        return {"success": False, "error": f"An internal server error occurred during search retrieval: {str(e)}"}
