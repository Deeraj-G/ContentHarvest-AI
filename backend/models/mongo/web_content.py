from datetime import datetime
from typing import Dict, Any
from uuid import UUID
from beanie import Document
from pydantic import Field


class WebContent(Document):
    """
    MongoDB document model for storing web content.
    """

    tenant_id: UUID = Field(description="Tenant ID for multi-tenancy")
    url: str = Field(description="Source URL of the content")
    raw_text: str = Field(description="Original scraped text content")
    headings: Dict[str, Any] = Field(
        default_factory=dict, description="List of headings from the page"
    )
    metadata: Dict[str, Any] | None = Field(
        default_factory=dict, description="Additional metadata about the content"
    )
    llm_cleaned_content: Dict[str, Any] | None = Field(
        default_factory=dict, description="Processed and structured content from LLM"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        """
        Settings for the WebContent model.
        """

        name = "web_content"
        use_state_management = True
