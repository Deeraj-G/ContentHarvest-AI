"""
This file contains the RAG pipeline.
"""

import os
import uuid

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct

load_dotenv()

QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")


class QdrantVectorStore:
    """
    Qdrant vector store implementation for managing vector embeddings
    Handles connection, data insertion, and search operations with a Qdrant database
    """

    def __init__(self, tenant_id, *args, **kwargs):
        """
        Initialize the vector store

        Args:
            tenant_id: Identifier for the organization/tenant
            *args, **kwargs: Additional arguments passed to parent class
        """
        super().__init__(*args, **kwargs)
        self.tenant_id = tenant_id
        self.client = self.connect()

    def connect(self):
        """
        Establish connection to the Qdrant vector store

        Returns:
            QdrantClient: Connected client instance

        Raises:
            Exception: If connection fails
        """
        if self.client is None:
            try:
                qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
                self.client = qdrant_client
            except Exception as e:
                raise e

        return self.client

    