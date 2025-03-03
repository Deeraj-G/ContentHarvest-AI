"""
This file contains the MongoDB models and operations using Beanie ODM.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorClient

from backend.models.mongo.web_content import WebContent


class MongoDBManager:
    """
    Manager class for MongoDB operations.
    """

    _client: Optional[AsyncIOMotorClient] = None

    @classmethod
    def set_client(cls, client: AsyncIOMotorClient) -> None:
        """Set the MongoDB client instance"""
        cls._client = client

    @classmethod
    async def close_mongodb(cls) -> None:
        """Close the MongoDB connection"""
        if cls._client is not None:
            cls._client.close()
            cls._client = None

    @staticmethod
    async def insert_web_content(
        url: str,
        raw_text: str,
        headings: List[Dict[str, Any]],
        llm_raw_response: Dict[str, Any],
        processed_content: Dict[str, Any],
        metadata: Dict[str, Any],
        tenant_id: Optional[UUID] = None,
    ) -> WebContent:
        """
        Insert web content into MongoDB.

        Args:
            url: Source URL of the content
            text: Original scraped text
            headings: List of headings from the page
            llm_response: Raw LLM response and metadata
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            WebContent: Created document instance
        """
        content = WebContent(
            tenant_id=tenant_id,
            url=url,
            raw_text=raw_text,
            headings=headings,
            llm_raw_response=llm_raw_response,
            processed_content=processed_content,
            metadata=metadata,
        )
        return await content.insert()

    @staticmethod
    async def get_content_by_url(url: str, tenant_id: UUID = None) -> List[WebContent]:
        """
        Retrieve content by URL.

        Args:
            url: URL to search for

        Returns:
            List[WebContent]: List of found documents
        """
        return await WebContent.find(
            WebContent.url == url, WebContent.tenant_id == tenant_id
        ).to_list()
