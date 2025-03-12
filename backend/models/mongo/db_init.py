"""
This file contains the initialization code for MongoDB connection using Beanie.
"""

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from backend.models.mongo.db_manager import MongoDBManager
from backend.models.mongo.web_content import WebContent


async def init_mongodb(mongodb_url: str, database_name: str):
    """
    Initialize MongoDB connection and Beanie ODM.

    Args:
        mongodb_url: MongoDB connection URL
        database_name: Name of the database to use
    """
    # Create Motor client
    client = AsyncIOMotorClient(mongodb_url)
    MongoDBManager.set_client(client)

    # Initialize Beanie with the MongoDB client
    await init_beanie(
        database=client[database_name],
        document_models=[WebContent],  # Add all document models here
    )
