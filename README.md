# BrowserBud 🧠

**AI-powered pipeline for transforming web research into structured Notion notes with intelligent cross-references and knowledge graphs.**

Transform scattered browser captures into comprehensive, interconnected notes that build your personal knowledge base over time. Capture notes from the browser with the BrowserBud Chrome Extension: https://github.com/srinath1510/browserbud-chrome-extension

## Features

- **🔄 Smart Batch Processing**: Reduces AI API calls by 80% through intelligent content batching
- **🧠 Knowledge Graph**: Builds connections between concepts across all your research sessions  
- **📝 Rich Notion Integration**: Creates structured databases with automatic cross-references
- **⚡ Real-time API**: FastAPI server for browser extension integration
- **🔍 Historical Context**: Links new learning to your existing knowledge base
- **🎯 Intent-Aware Processing**: Adapts analysis based on your learning goals (research, reference, learn)

## Quick Start

### 1. Prerequisites

- **Python 3.9+**
- **Docker** (recommended for Neo4j)
- **API Keys**:
  - [Anthropic Claude](https://console.anthropic.com/) for AI processing
  - [Notion Integration](https://www.notion.so/my-integrations) for note generation

### 2. Installation

```bash
git clone <repository-url>
cd pocketflow-note-agent

# Automated setup (recommended)
chmod +x setup.sh
./setup.sh
```

**Manual Setup:**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

### 3. Configuration

Edit `.env` with your credentials:

```bash
# Required API Keys
ANTHROPIC_API_KEY=your_anthropic_key_here
NOTION_TOKEN=your_notion_integration_token

# Database (Neo4j)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password

# Optional: LLM Provider
LLM_PROVIDER=anthropic
```

### 4. Start Services

```bash
# Start Neo4j database
docker-compose up -d neo4j

# Activate virtual environment
source venv/bin/activate

# Start API server
python start_fastapi.py
```

The API will be available at `http://localhost:8000`

## Usage

### Direct Pipeline Usage

Process web captures directly:

```python
from main import NoteGenerationPipeline

# Initialize pipeline
pipeline = NoteGenerationPipeline()

# Process captures
captures = [
    {
        "content": "Machine learning is a subset of AI...",
        "user_id": "your_user_id",
        "source_url": "https://example.com/ml-guide",
        "title": "ML Guide",
        "intent": "learn"  # or "research", "reference"
    }
]

result = pipeline.run(captures)
print(f"Session: {result['session_id']}")
```

### API Usage

**Submit captures for processing:**
```bash
curl -X POST "http://localhost:8000/api/v1/bake" \
  -H "Content-Type: application/json" \
  -d '{
    "captures": [
      {
        "content": "Your web content here...",
        "user_id": "user123",
        "source_url": "https://example.com",
        "title": "Article Title",
        "intent": "learn"
      }
    ],
    "user_id": "user123"
  }'
```

**Check processing status:**
```bash
curl "http://localhost:8000/api/v1/bake/{bake_id}/status"
```

## Architecture

### Pipeline Flow

```
Browser Captures → Capture Ingestion → Content Analysis → Knowledge Graph → Historical Knowledge → Notion Generation
```

### Node Details

1. **Capture Ingestion**: Cleans HTML, extracts metadata, validates input format
2. **Content Analysis**: AI-powered concept extraction with batch optimization  
3. **Knowledge Graph**: Stores concepts and relationships in Neo4j
4. **Historical Knowledge**: Connects new learning to existing knowledge
5. **Notion Generation**: Creates structured databases and interconnected pages

### Key Optimizations

- **Batch Processing**: Groups similar content for single AI calls
- **Smart Caching**: Reuses analysis for similar content patterns
- **Rule-based Pre-filtering**: Skips AI for simple categorization
- **Connection Reuse**: Efficiently manages database and API connections

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API key | ✅ | - |
| `NOTION_TOKEN` | Notion integration token | ✅ | - |
| `NEO4J_URI` | Neo4j connection URI | ✅ | `bolt://localhost:7687` |
| `NEO4J_PASSWORD` | Neo4j password | ✅ | - |
| `NEO4J_USER` | Neo4j username | ❌ | `neo4j` |
| `LLM_PROVIDER` | LLM provider to use | ❌ | `anthropic` |

### Pipeline Configuration

Create `config/custom_config.json`:

```json
{
  "processing": {
    "batch_size": 5,
    "enable_caching": true,
    "content_analysis_timeout": 30
  },
  "notion": {
    "create_master_pages": true,
    "enable_cross_references": true
  },
  "neo4j": {
    "connection_timeout": 10,
    "max_retry_attempts": 3
  }
}
```

## API Reference

### Core Endpoints

- `POST /api/v1/bake` - Submit captures for processing
- `GET /api/v1/bake/{bake_id}/status` - Check processing status
- `GET /api/v1/bake/{bake_id}/result` - Get processing results
- `GET /health` - Service health check

### Data Models

**Capture Input:**
```json
{
  "content": "string",
  "user_id": "string", 
  "source_url": "string",
  "title": "string",
  "intent": "learn|research|reference",
  "user_note": "string (optional)"
}
```

**Processing Result:**
```json
{
  "session_id": "string",
  "status": "completed|failed|processing",
  "notion_pages": ["urls"],
  "concepts_extracted": 15,
  "knowledge_connections": 8,
  "processing_time": 2.5
}
```

## Development

### Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
pytest tests/test_error_handling.py  # Error scenarios
```

### Project Structure

```
├── main.py                 # Pipeline orchestrator
├── nodes/                  # Processing nodes
│   ├── capture_ingestion.py
│   ├── content_analysis.py
│   ├── knowledge_graph.py
│   ├── historical_knowledge_retrieval.py
│   ├── notion_note_generation.py
│   └── notion/            # Notion integration modules
├── api/                   # FastAPI application
├── config/               # Configuration management
├── tests/               # Comprehensive test suite
└── data/               # Processing artifacts and database
```

## Troubleshooting

### Common Issues

**Neo4j Connection Failed**
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Restart Neo4j
docker-compose restart neo4j

# Check logs
docker logs browserbud_neo4j
```

**API Rate Limits**
- The pipeline includes automatic retry logic and batch optimization
- Monitor usage in logs: `tail -f logs/pipeline.log`

**Missing Notion Permissions**
- Ensure your Notion integration has read/write access to your workspace
- Share specific pages with your integration if needed

### Performance Tuning

- **Increase batch size** for fewer API calls (may use more memory)
- **Enable caching** for repeated similar content
- **Adjust timeouts** for slower internet connections

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and add tests
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT License - see [LICENSE.md](LICENSE.md) for details.

---

**Need help?** [Open an issue](https://github.com/your-repo/issues) or check the [documentation](https://your-docs-url.com).
