"""
Host the FastAPI app.
"""

import os
from uuid import UUID
from contextlib import asynccontextmanager
from http import HTTPStatus
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from loguru import logger

from backend.content.content_processor import (
    vectorize_and_store_web_content,
    scrape_url,
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
    yield
    await MongoDBManager.close_mongodb()


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
async def scrape_endpoint(tenant_id: str, url: str = Form(...)):
    """
    This endpoint handles the web scraper.
    """

    if not tenant_id:
        return {
            "content": {
                "success": False,
                "error": "Tenant ID is required",
            },
            "status": HTTPStatus.BAD_REQUEST,
        }

    try:
        logger.info(f"web scrape started for tenant: {tenant_id}")
        scrape_result = await scrape_url(url)  # This is sync
        if not scrape_result["success"]:
            return {
                "content": {
                    "success": False,
                    "error": f"Scraping failed: {scrape_result['error']}",
                },
                "status": HTTPStatus.BAD_REQUEST,
            }

        process_result = await vectorize_and_store_web_content(
            scrape_result, tenant_id=UUID(tenant_id)
        )
        return {"content": process_result, "status": HTTPStatus.OK}
    except Exception as e:
        return {
            "content": {
                "success": False,
                "error": f"Error during processing: {str(e)}",
            },
            "status": HTTPStatus.INTERNAL_SERVER_ERROR,
        }
