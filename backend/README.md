## Backend Overview

The backend implements a web content processing pipeline that:

1. Scrapes content from URLs
2. Processes the content using LLMs to extract structured information
3. Stores both raw and processed content in MongoDB
4. Creates vector embeddings of the content and stores them in Qdrant
5. Provides search capabilities through vector similarity

The system is designed with multi-tenancy in mind, with tenant IDs used to separate data between different users or organizations.

## Project Structure

The backend is organized into several folders, each with a specific responsibility:

### `/content/`

This folder contains functionality for processing web content.

- **`content_processor.py`**: Core functionality for the content processor. Handles scraping web pages, extracting relevant text and headings, vectorizing content for efficient search, storing content in MongoDB, and managing interactions with the Qdrant vector store. Essential for the content ingestion pipeline that transforms raw web data into structured, searchable information.

- **`prompts.py`**: Contains prompt templates for the content processor. Provides system and user prompts for the LLM to analyze and extract key information from documents based on headings and text content.

### `/fastapi_app/`

This folder contains the FastAPI application.

- **`main.py`**: Hosts the FastAPI application. Initializes the MongoDB connection, sets up CORS middleware, and defines API endpoints. The main endpoint `/v1/tenants/{tenant_id}/harvest/` allows harvesting content from a URL for a specific tenant.

### `/models/`

This folder contains database models and data access layers.

#### `/models/mongo/`

MongoDB-related models and operations.

- **`db_init.py`**: Contains initialization code for MongoDB connection using Beanie ODM.

- **`db_manager.py`**: Provides a manager class for MongoDB operations using Beanie ODM. Handles operations like inserting web content and retrieving content by URL and tenant ID.

- **`web_content.py`**: Defines the MongoDB document model for storing web content. Includes fields for tenant ID, URL, raw text, headings, metadata, and LLM-processed content.

#### `/models/rag/`

Retrieval-Augmented Generation (RAG) related models.

- **`qdrant.py`**: Implements the RAG pipeline using Qdrant vector database. Handles connection to Qdrant, insertion of vector embeddings, and search operations for retrieving relevant content.

### `/services/`

This folder contains utility services used across the application.

- **`embedding_utils.py`**: Provides utility functions for generating and working with embeddings. Contains a function to get embeddings from OpenAI API.

- **`vector_schemas.py`**: Contains Pydantic models for the application. Defines classes for vector payloads and content processing, with methods to add, retrieve, and clear payloads.
