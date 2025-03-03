from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from beanie import Document
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
