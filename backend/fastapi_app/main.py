"""
Host the FastAPI app.
"""

import os
from contextlib import asynccontextmanager
from http import HTTPStatus
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.content.content_processor import (
    scrape_url,
    vectorize_and_store_web_content,
)
from backend.models.mongo.db_init import init_mongodb
from backend.models.mongo.db_manager import MongoDBManager

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")

app = FastAPI()


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Lifecycle manager for FastAPI app"""
    await init_mongodb(MONGODB_URL, DATABASE_NAME)
    logger.info("MongoDB connection initialized")
    yield
    logger.info("Shutting down MongoDB connection")
    await MongoDBManager.close_mongodb()


# Update the original app declaration with lifespan
app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.post("/v1/tenants/{tenant_id}/scrape/")
async def scrape_endpoint(tenant_id: UUID, url: str = Form(...)):
    """
    Scrape content from a URL and process it for a specific tenant.

    Args:
        tenant_id: The UUID of the tenant
        url: The URL to scrape

    Returns:
        dict: Result of the scraping and processing operation
    """
    try:
        logger.info(f"Web scrape started for tenant: {tenant_id}")
        scrape_result = await scrape_url(url)

        if not scrape_result["success"]:
            return {
                "content": {
                    "success": False,
                    "error": f"Scraping failed: {scrape_result['error']}",
                    "status_code": scrape_result["status_code"],
                },
                "status": scrape_result["status_code"],
            }

        process_result = await vectorize_and_store_web_content(
            scrape_result, tenant_id=tenant_id  # No need to convert to UUID again
        )
        return {"content": process_result, "status": HTTPStatus.OK}
    except Exception as e:
        logger.error(f"Error during scraping process: {str(e)}")
        return {
            "content": {
                "success": False,
                "error": f"Error during processing: {str(e)}",
            },
            "status": HTTPStatus.INTERNAL_SERVER_ERROR,
        }
