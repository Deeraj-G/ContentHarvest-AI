"""
This file contains the MongoDB models and operations using Beanie ODM.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from beanie import Document
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import Field


class WebContent(Document):
    """
    MongoDB document model for storing web content.
    """

    tenant_id: Optional[UUID] = Field(
        default=None, description="Tenant ID for multi-tenancy"
    )
    url: str = Field(description="Source URL of the content")
    raw_text: str = Field(description="Original scraped text content")
    headings: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of headings from the page"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about the content"
    )
    llm_raw_response: str = Field(
        description="Original response from LLM before processing"
    )
    processed_content: Dict[str, Any] = Field(
        default_factory=dict, description="Processed and structured content from LLM"
    )
    created_at: datetime = Field(default_factory=datetime.now())
    updated_at: datetime = Field(default_factory=datetime.now())

    class Settings:
        """
        Settings for the WebContent model.
        """

        name = "web_content"
        use_state_management = True


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
        return await WebContent.find(WebContent.url == url, WebContent.tenant_id == tenant_id).to_list()
