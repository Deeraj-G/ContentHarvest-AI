"""
Utility functions for generating and working with embeddings.
"""

import os
from typing import List

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.create_embedding_response import CreateEmbeddingResponse

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


def get_embedding(text: str) -> List[float]:
    """
    Get embedding from OpenAI API

    Args:
        text (str): The text to generate an embedding for

    Returns:
        List[float]: The embedding vector
    """
    response: CreateEmbeddingResponse = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding
