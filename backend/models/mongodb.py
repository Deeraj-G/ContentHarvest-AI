"""
This file contains the MongoDB models and operations using Beanie ODM.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from beanie import Document
from pydantic import Field


class WebContent(Document):
    """
    MongoDB document model for storing web content.
    """
    tenant_id: Optional[UUID] = Field(default=None, description="Tenant ID for multi-tenancy")
    url: str = Field(description="Source URL of the content")
    original_text: str = Field(description="Original scraped text content")
    headings: List[Dict[str, Any]] = Field(default_factory=list, description="List of headings from the page")
    processed_content: Dict[str, Any] = Field(default_factory=dict, description="Processed and structured content")
    created_at: datetime = Field(default_factory=datetime.now())
    updated_at: datetime = Field(default_factory=datetime.now())

    class Settings:
        name = "web_content"
        use_state_management = True


class MongoDBManager:
    """
    Manager class for MongoDB operations.
    """
    @staticmethod
    async def insert_web_content(
        url: str,
        original_text: str,
        headings: List[Dict[str, Any]],
        processed_content: Dict[str, Any],
        tenant_id: Optional[UUID] = None
    ) -> WebContent:
        """
        Insert web content into MongoDB.

        Args:
            url: Source URL of the content
            original_text: Original scraped text
            headings: List of headings from the page
            processed_content: Processed and structured content
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            WebContent: Created document instance
        """
        content = WebContent(
            tenant_id=tenant_id,
            url=url,
            original_text=original_text,
            headings=headings,
            processed_content=processed_content
        )
        return await content.insert()

    @staticmethod
    async def get_content_by_url(url: str) -> Optional[WebContent]:
        """
        Retrieve content by URL.

        Args:
            url: URL to search for

        Returns:
            Optional[WebContent]: Found document or None
        """
        return await WebContent.find_one(WebContent.url == url)

    @staticmethod
    async def get_content_by_tenant(tenant_id: UUID) -> List[WebContent]:
        """
        Retrieve all content for a specific tenant.

        Args:
            tenant_id: Tenant ID to filter by

        Returns:
            List[WebContent]: List of found documents
        """
        return await WebContent.find(WebContent.tenant_id == tenant_id).to_list() 