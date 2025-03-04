"""
This file contains the MongoDB models and operations using Beanie ODM.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger

from backend.models.mongo.web_content import WebContent


class MongoDBManager:
    """
    Manager class for MongoDB operations.
    """

    _client: Optional[AsyncIOMotorClient] = None

    @classmethod
    def set_client(cls, client: AsyncIOMotorClient) -> None:
        """Set the MongoDB client instance"""
        logger.info("Setting MongoDB client")
        cls._client = client

    @classmethod
    async def close_mongodb(cls) -> None:
        """Close the MongoDB connection"""
        if cls._client is not None:
            logger.info("Closing MongoDB connection")
            cls._client.close()
            cls._client = None

    @staticmethod
    async def insert_web_content(
        url: str,
        tenant_id: UUID,
        raw_text: str,
        headings: Dict[str, Any],
        llm_cleaned_content: Dict[str, Any] | None = None,
        metadata: Dict[str, Any] | None = None,
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
            llm_cleaned_content=llm_cleaned_content,
            metadata=metadata,
        )
        return await content.insert()

    @staticmethod
    async def get_content_by_url_and_tenant_id(
        url: str, tenant_id: UUID
    ) -> List[WebContent]:
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
