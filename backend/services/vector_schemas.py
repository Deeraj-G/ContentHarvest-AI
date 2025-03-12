"""
This file contains the Pydantic models for the application.
"""

from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID
from pydantic import BaseModel

from backend.services.embedding_utils import get_embedding


class VectorPayload(BaseModel):
    """
    This class is used to store the vector payloads in the format expected by Qdrant.
    """

    vector: List[float]
    payload: Dict[str, Any]


class ContentProcessor(BaseModel):
    """
    This class is used to process the content and store it in Qdrant.
    """

    tenant_id: UUID
    vector_payloads: List[VectorPayload] = []

    def add_payload(self, content: dict, url: str) -> None:
        """
        Add a new payload to the vector_payloads list.

        Args:
            content (dict): The content to be stored
            url (str): The source URL
        """
        vector = get_embedding(content["input_text"])

        payload = VectorPayload(
            vector=vector,
            payload={
                "url": url,
                "tenant_id": self.tenant_id,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            },
        )
        self.vector_payloads.append(payload)

    def get_payloads(self) -> List[Dict[str, Any]]:
        """
        Get the vector payloads in the format expected by Qdrant.

        Returns:
            List[Dict[str, Any]]: List of vector payloads
        """
        return [payload.model_dump() for payload in self.vector_payloads]

    def clear_payloads(self) -> None:
        """
        Clear all stored payloads.
        """
        self.vector_payloads = []