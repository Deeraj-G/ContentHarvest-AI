"""
This file contains the initialization code for MongoDB connection using Beanie.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from backend.models.mongodb import WebContent, MongoDBManager


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
