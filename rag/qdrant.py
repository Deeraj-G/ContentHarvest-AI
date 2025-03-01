"""
This file contains the RAG pipeline.
"""

import os
import uuid

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct
from loguru import logger

load_dotenv()

QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")


class QdrantVectorStore:
    """
    Qdrant vector store implementation for managing vector embeddings
    Handles connection, data insertion, and search operations with a Qdrant database
    """

    def __init__(self, tenant_id: str, *args, **kwargs):
        """
        Initialize the vector store

        Args:
            tenant_id: Identifier for the organization/tenant
            *args, **kwargs: Additional arguments passed to parent class
        """
        super().__init__(*args, **kwargs)
        self.tenant_id = tenant_id
        self.client = self.connect()  # Now connect and assign the client

    def connect(self):
        """
        Establish connection to the Qdrant vector store

        Returns:
            QdrantClient: Connected client instance

        Raises:
            Exception: If connection fails
        """
        try:
            qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            return qdrant_client
        except Exception as e:
            raise Exception(f"Failed to connect to Qdrant: {str(e)}")

    def insert_data_to_qdrant(self, vector_payloads: list, collection_name: str):
        """
        Insert vector embeddings and their associated payloads into Qdrant

        Args:
            collection_name (str): Name of the collection to insert data into
            vector_payload (list): List of dictionaries containing vectors and payloads
                                   Each dict should have 'vector' and 'payload' keys

        Returns:
            info: Response from Qdrant about the insertion operation
        """
        session_id = str(uuid.uuid4())  # Create one session_id for the group
        try:
            info = self.client.upsert(
                collection_name=collection_name,
                wait=True,  # Wait for operation to complete
                points=[
                    PointStruct(
                    id=str(uuid.uuid4()),  # Unique ID for each point
                    vector=vector_set.get("vector"),
                    payload={
                        **vector_set.get("payload", {}),  # Spread existing payload
                        "session_id": session_id  # Add session_id to payload
                    }
                )
                    for vector_set in vector_payloads
                ],
            )

            return info
        except Exception as e:
            logger.error(f"Error inserting data to Qdrant: {e}")
            raise e

    def search_data_from_qdrant(
        self, collection_name: str, query: str, tenant_id: str = None, limit: int = 5
    ):
        """
        Search data from Qdrant vector database

        Args:
            collection_name (str): Name of the Qdrant collection to search in
            query (str): The search query text
            tenant_id (str): Optional filter to search for specific tenant_id
            limit (int): Maximum number of results to return (default: 10)

        Returns:
            List of search results from Qdrant, ordered by relevance
        """
        # Initialize empty filter list for search conditions
        filter_list = []

        # If tenant_id is provided, add it as a filter condition
        if tenant_id:
            filter_list.append(
                models.FieldCondition(
                    key="tenant_id", match=models.MatchValue(value=tenant_id)
                )
            )

        # Perform the search using Qdrant client
        return self.client.search(
            collection_name=collection_name,
            query_vector=query,
            tenant_id=tenant_id,
            limit=limit,
        )
