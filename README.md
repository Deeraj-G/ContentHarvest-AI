# ContentHarvest AI

A full-stack web application for harvesting, processing, and storing web content into a structured format with advanced features including content vectorization and multi-tenant support.

## Features

- **Content Harvesting**: Extract content from any URL using BeautifulSoup4
- **Content Processing**: Analyze and process web content
- **Vector Storage**: Store processed content in vector database (Qdrant)
- **MongoDB Integration**: Persist metadata and results
- **Multi-tenant Architecture**: Support for multiple tenants with isolated data
- **Modern React Frontend**: User-friendly interface built with React and TypeScript
- **RESTful API**: FastAPI backend with well-defined endpoints

## Architecture

### Backend

- **FastAPI**: Modern, high-performance web framework
- **MongoDB**: Document database for storing metadata and results
- **Qdrant**: Vector database for semantic search capabilities
- **OpenAI Integration**: For content analysis and processing

### Frontend

- **React**: Component-based UI library
- **TypeScript**: Type-safe JavaScript
- **React Router**: For client-side routing

## Prerequisites

- Python 3.9+
- Node.js 16+
- MongoDB
- Qdrant (optional, for vector storage)

## Installation

### Backend

```bash
# Create and activate virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Copy .env.example to .env and update the values
```

### Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

## Usage

### Start the Backend Server

```bash
# Start the FastAPI server
uvicorn backend.fastapi_app.main:app --reload
```

### Start the Frontend Development Server

```bash
# Navigate to frontend directory
cd frontend

# Start the development server
npm start
```

### API Endpoints

- `POST /v1/tenants/{tenant_id}/scrape/`: Scrape and process content from a URL

### Using the Application

1. Open your browser and navigate to `http://localhost:3000`
2. From the dashboard, click on the Web Scraper Tool
3. Enter a URL to scrape
4. View the processed results

### Command Line Usage

```bash
# Execute a curl POST request to the server
curl -v http://localhost:8000/v1/tenants/66efb688-8cd2-4381-9400-31a7b61e6209/scrape/ -H "Content-Type: application/x-www-form-urlencoded" -d "url=https://en.wikipedia.org/wiki/Artificial_intelligence"
```

## Development

### Project Structure

```
web_scraper/
├── backend/
│   ├── content/           # Content processing logic
│   ├── fastapi_app/       # FastAPI application
│   ├── models/            # Database models
│   └── services/          # Business logic services
├── frontend/
│   ├── public/            # Static assets
│   └── src/               # React components and logic
└── requirements.txt       # Python dependencies
```

## License

[GNU AGPLv3](LICENSE)
